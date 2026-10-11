"""
NaviStudo Backend - Model 1 Integration (Free-text Extraction).

This module provides the interface for Model 1, which extracts structured
information from students' free-text answers.

Oumnia will implement the actual AI prompt logic in this file.
The interface (analyze method signature) must remain stable.

Input: Student's free-text answers with question identifiers and context.
Output: Structured information extracted from those answers.
"""

from app.schemas.model_one_schema import ModelOneInput, ModelOneOutput


class ModelOneClient:
    """Client for Model 1 (Free-text Extraction).

    Oumnia: Implement the `analyze` method with your prompt logic.
    The method signature and return type must remain as defined.
    """

    def analyze(self, input_data: ModelOneInput) -> ModelOneOutput:
        """Analyze free-text answers and extract structured information.

        Args:
            input_data: Contains:
                - free_text_answers: dict[question_id, answer_text]
                - question_context: dict[question_id, context_text] (optional)
                - school_year: int (1, 2, or 3)
                - current_branch: str or None

        Returns:
            ModelOneOutput with:
                - extracted_data: dict with structured information (schema TBD by Oumnia)
                - metadata: optional dict with confidence scores, etc.
                - success: bool
                - error: str or None if failed

        Raises:
            This method should not raise exceptions. Return success=False with error message instead.
        """
        # TODO(Oumnia): Implement the actual AI prompt logic here.
        # 1. Construct prompt from input_data.free_text_answers and context
        # 2. Call your chosen model (OpenAI, Anthropic, local, etc.)
        # 3. Parse model response into structured extracted_data
        # 4. Return ModelOneOutput with extracted_data, metadata, success=True
        # 5. On failure, return ModelOneOutput(success=False, error="...")

        # Placeholder - replace with actual implementation
        return ModelOneOutput(
            success=False,
            error="Model 1 not yet implemented. Oumnia to implement analyze() method.",
            extracted_data={},
            metadata={},
        )


# Convenience function for direct use if preferred
def analyze_free_text(input_data: ModelOneInput) -> ModelOneOutput:
    """Standalone function wrapper for Model 1 analysis.

    Can be used instead of the class if preferred.
    """
    client = ModelOneClient()
    return client.analyze(input_data)


class ModelOneError(Exception):
    """Raised when Model 1 processing fails (for orchestrator to catch)."""

    pass