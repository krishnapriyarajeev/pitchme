"""Voice cloning: stronger answers played back in the user's own voice.

The user's voice is cloned once from their onboarding sample. After a
call, each answer the content judge flagged is rewritten and spoken in
that voice; a solo talk can also be lightly corrected and re-spoken.

    from ai.voice_cloning import correct_answers, speak_answers
    fixes = correct_answers(content_report.needs_work)
    clips = speak_answers(fixes, user.voice_clone_id)
"""

from .answers import AnswerCorrection, correct_answers
from .base import EMOTIONS, ProsodyParams, VoiceCloneClient, VoiceCloneError, VoiceSample
from .playback import AnswerPlayback, speak_answers, speak_script
from .script import ScriptSegment, correct_script

__all__ = [
    "EMOTIONS",
    "AnswerCorrection",
    "AnswerPlayback",
    "ProsodyParams",
    "ScriptSegment",
    "VoiceCloneClient",
    "VoiceCloneError",
    "VoiceSample",
    "correct_answers",
    "correct_script",
    "speak_answers",
    "speak_script",
]
