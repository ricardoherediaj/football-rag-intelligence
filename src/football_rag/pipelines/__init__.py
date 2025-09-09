"""High-level pipelines of the project."""

# %% IMPORTS

from llmops_project.pipelines.deployment.deploy_model import DeployModelJob
from llmops_project.pipelines.deployment.register_model import LogAndRegisterModelJob
from llmops_project.pipelines.feature_engineering.create_vector_db import CreateVectorDBJob
from llmops_project.pipelines.feature_engineering.ingest_documents import IngestAndUpdateVectorDBJob
from llmops_project.pipelines.managers.deployment_manager import DeploymentJob
from llmops_project.pipelines.managers.feature_engineering_manager import FeatureEngineeringJob
from llmops_project.pipelines.managers.monitoring_manager import MonitoringJob
from llmops_project.pipelines.monitoring.generate_rag_dataset import GenerateRagDatasetJob
from llmops_project.pipelines.monitoring.post_deploy_eval import MonitoringEvalJob
from llmops_project.pipelines.monitoring.pre_deploy_eval import EvaluateModelJob

# %% TYPES

JobKind = (
    DeploymentJob
    | FeatureEngineeringJob
    | GenerateRagDatasetJob
    | EvaluateModelJob
    | CreateVectorDBJob
    | IngestAndUpdateVectorDBJob
    | DeployModelJob
    | LogAndRegisterModelJob
    | MonitoringEvalJob
    | MonitoringJob
)

# %% EXPORTS

__all__ = [
    "DeploymentJob",
    "FeatureEngineeringJob",
    "GenerateRagDatasetJob",
    "EvaluateModelJob",
    "CreateVectorDBJob",
    "IngestAndUpdateVectorDBJob",
    "DeployModelJob",
    "LogAndRegisterModelJob",
    "MonitoringEvalJob",
    "MonitoringJob",
    "JobKind",
]
