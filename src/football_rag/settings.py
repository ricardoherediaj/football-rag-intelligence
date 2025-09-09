"""Define settings for the application."""

# %% IMPORTS

import pydantic as pdt
import pydantic_settings as pdts

from llmops_project import pipelines

# %% SETTINGS


class Settings(pdts.BaseSettings, strict=True, frozen=True, extra="allow"):  # type: ignore[misc]
    """Base class for application settings.

    Use settings to provide high-level preferences.
    i.e., to separate settings from provider (e.g., CLI).
    """


class MainSettings(Settings):  # type: ignore[misc]
    """Main settings of the application.

    Parameters:
        job (jobs.JobKind): job to run.
    """

    job: pipelines.JobKind = pdt.Field(..., discriminator="KIND")
