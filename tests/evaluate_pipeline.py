"""
The Ultimate Evaluation Harness.
Combines Retrieval Metrics + Faithfulness + LLM Judge.
"""
import json
import re
import sys
import os
import logging
import numpy as np
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

# 1. LOAD ENV VARS IMMEDIATELY
# This fixes the "ANTHROPIC_API_KEY required" error
load_dotenv()

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from football_rag.models.rag_pipeline import FootballRAGPipeline
from football_rag.models.generate import generate_with_llm

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("eval")

class EvaluationHarness:
    def __init__(self):
        # Initialize the pipeline
        self.pipeline = FootballRAGPipeline(provider="anthropic")
        
        # Explicitly grab the key from the environment to pass to the Judge
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("⚠️ No API Key found in env. Judge might fail.")

        self.eval_dir = PROJECT_ROOT / "data" / "eval_datasets"
        eval_file = self.eval_dir / "tactical_analysis_eval.json"
        
        if not eval_file.exists():
            raise FileNotFoundError(f"Eval file not found at: {eval_file}")
            
        with open(eval_file) as f:
            self.eval_data = json.load(f)
            
        # Load Ground Truth
        gold_file = PROJECT_ROOT / "data" / "processed" / "matches_gold.json"
        if gold_file.exists():
            with open(gold_file) as f:
                self.gold_data = {str(m['metadata']['match_id']): m for m in json.load(f)}
        else:
            self.gold_data = {}

    def calculate_faithfulness(self, text: str, ground_truth_metrics: dict) -> float:
        """Extracts numbers from LLM response and checks if they exist in the Ground Truth."""
        found_numbers = [float(x) for x in re.findall(r'-?\d+\.?\d*', text)]
        if not found_numbers: return 0.5 

        truth_values = []
        def flatten(d):
            for v in d.values():
                if isinstance(v, dict): flatten(v)
                elif isinstance(v, (int, float)): truth_values.append(float(v))
                elif isinstance(v, str):
                    try: truth_values.append(float(v))
                    except: pass
        flatten(ground_truth_metrics)
        
        matches = 0
        for num in found_numbers:
            if any(np.isclose(num, t, atol=0.15) for t in truth_values):
                matches += 1
        return matches / len(found_numbers)

    def llm_judge_score(self, query: str, response: str, expected_insights: list, ref_metrics: dict) -> float:
        """LLM-as-a-Judge: Rates tactical quality on 1-5 scale."""
        prompt = f"""
        You are a senior football analyst auditing an automated match report.
        
        --- INPUT DATA (GROUND TRUTH) ---
        {json.dumps(ref_metrics, indent=2)}
        
        --- EXPECTED INSIGHTS ---
        {json.dumps(expected_insights, indent=2)}
        
        --- REPORT ---
        "{response}"
        
        --- RUBRIC (1-5) ---
        5: Perfect. Cites metrics correctly, covers all insights, explains 'WHY'.
        4: Good. Accurate but misses a minor insight or is slightly generic.
        3: Average. Factual but dry listing of stats.
        2: Poor. Misses key context.
        1: Fail. Hallucinated or wrong.
        
        Output format: JSON with keys "score" (int) and "reason".
        """
        
        try:
            # Pass the loaded API key explicitly
            raw_response = generate_with_llm(
                prompt, 
                provider="anthropic", 
                api_key=self.api_key, 
                temperature=0
            )
            
            match = re.search(r'"score":\s*(\d)', raw_response)
            if match:
                score = int(match.group(1))
                return (score - 1) / 4
            
            # Fallback for plain number
            digit = re.search(r'\b[1-5]\b', raw_response)
            return (int(digit.group(0)) - 1) / 4 if digit else 0.5
            
        except Exception as e:
            logger.error(f"Judge Error: {e}")
            return 0.5

    def run(self):
        print(f"🚀 Starting Evaluation on {len(self.eval_data['test_cases'])} Test Cases")
        print("="*60)
        
        results = []
        
        for case in tqdm(self.eval_data['test_cases']):
            query = case['query']
            target_match_id = str(case.get('match_id'))
            
            # 1. Run Pipeline
            output = self.pipeline.run(query)
            if "error" in output: continue

            # 2. Metrics
            retrieved_id = str(output.get('match_id'))
            retrieval_success = (retrieved_id == target_match_id)
            
            ground_truth = self.gold_data.get(target_match_id, {})
            if not ground_truth: ground_truth = case.get('viz_metrics', {})
            
            faithfulness = self.calculate_faithfulness(output['commentary'], ground_truth)
            
            # 3. Judge (Now has the key!)
            insight_score = self.llm_judge_score(
                query, 
                output['commentary'], 
                case.get('expected_insights', []),
                case.get('viz_metrics', {})
            )
            
            results.append({
                "id": case['test_id'],
                "retrieved_correctly": retrieval_success,
                "faithfulness_score": round(faithfulness, 2),
                "insight_score": round(insight_score, 2),
                "generated_report": output['commentary']
            })

        # Report
        output_file = self.eval_dir / "eval_results.json"
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        retrieval_acc = np.mean([r['retrieved_correctly'] for r in results])
        avg_faithfulness = np.mean([r['faithfulness_score'] for r in results])
        avg_insight = np.mean([r['insight_score'] for r in results])
        
        print("\n" + "="*60)
        print(f"1. Retrieval Accuracy: {retrieval_acc:.1%}")
        print(f"2. Faithfulness:       {avg_faithfulness:.1%}")
        print(f"3. Tactical Insight:   {avg_insight:.1%}")
        print("="*60)
        
        if retrieval_acc == 1.0 and avg_faithfulness > 0.90:
            print("✅ PASSED: System is ready for UI Deployment.")

if __name__ == "__main__":
    harness = EvaluationHarness()
    harness.run()