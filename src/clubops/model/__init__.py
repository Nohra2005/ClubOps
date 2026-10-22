"""The single path from ClubOps to a language model (D-01, D-02).

Every capability that needs a model goes through :class:`ModelClient`, so recording/replay,
output validation, cost counting and the per-plan budget are enforced in one tested place.
"""

from clubops.model.budget import Budget
from clubops.model.client import ModelClient, ModelRequest
from clubops.model.recordings import Recording, RecordingStore

__all__ = ["Budget", "ModelClient", "ModelRequest", "Recording", "RecordingStore"]
