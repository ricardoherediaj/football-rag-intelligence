import typing as T
from pathlib import Path

from llmops_project.pipelines import base
from llmops_project.pipelines.feature_engineering.create_vector_db import CreateVectorDBJob
from llmops_project.pipelines.feature_engineering.ingest_documents import IngestAndUpdateVectorDBJob


# %% Job class for logging and registering the RAG model
class FeatureEngineeringJob(base.Job):  # type: ignore[misc]
    """Job to log and register the RAG model in MLflow.

    Parameters:
        run_config (services.MlflowService.RunConfig): mlflow run config.
    """

    KIND: T.Literal["FeatureEngineeringJob"] = "FeatureEngineeringJob"

    embedding_model: str
    vector_store_path: str
    document_path: str
    collection_name: str

    @T.override
    def run(self) -> base.Locals:
        # Setup services
        # services
        # - logger
        logger = self.logger_service.logger()

        logger.info("Starting Feature Engineering Workflow")

        # Ensure the config path is relative to this script's location
        script_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        document_path = str(script_dir / self.document_path)

        logger.info("Creating Vector Database")

        # Create the vector database
        with CreateVectorDBJob(
            embedding_model=self.embedding_model,
            vector_store_path=self.vector_store_path,
            collection_name=self.collection_name,
        ) as create_vector_db_job:
            create_vector_db_job.run()

        # Ingest the documents
        with IngestAndUpdateVectorDBJob(
            embedding_model=self.embedding_model,
            vector_store_path=self.vector_store_path,
            collection_name=self.collection_name,
            document_path=document_path,
        ) as injest_job:
            injest_job.run()

        logger.success("Feature Engineering Workflow complete")

        return locals()


if __name__ == "__main__":
    # Test the pipeline

    from llmops_project import settings
    from llmops_project.io import configs

    script_dir = str(Path(__file__).parent.parent.parent.parent.parent)
    config_files = ["/rag_chain_config.yaml", "/feature_eng.yaml"]

    file_paths = [script_dir + "/confs/" + file for file in config_files]

    files = [configs.parse_file(file) for file in file_paths]

    config = configs.merge_configs([*files])  # type: ignore
    config["job"]["KIND"] = "FeatureEngineeringJob"  # type: ignore

    object_ = configs.to_object(config)  # python object

    setting = settings.MainSettings.model_validate(object_)

    with setting.job as runner:
        runner.run()
