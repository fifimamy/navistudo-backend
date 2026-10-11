"""
NaviStudo Backend - Model 2 Integration (Recommendation Ranking).

This module provides the interface for Model 2, which ranks academic
recommendations based on student profile, extracted info, and eligible options.

Oumnia will implement the actual AI prompt logic in this file.
The interface (rank method signature) must remain stable.

Input: Student's structured profile + Model 1 output + filtered knowledge-base options.
Output: Ranked recommendations with reasoning.
"""

from app.schemas.model_two_schema import ModelTwoInput, ModelTwoOutput, RankedRecommendation


class ModelTwoClient:
    """Client for Model 2 (Recommendation Ranking).

    Oumnia: Implement the `rank` method with your prompt logic.
    The method signature and return type must remain as defined.

    IMPORTANT: The returned recommendations MUST only contain option_ids
    that exist in the input eligible_options. Validation is performed
    by the orchestrator after this method returns.
    """

    def rank(self, input_data: ModelTwoInput) -> ModelTwoOutput:
        """Rank eligible academic options for the student.

        Args:
            input_data: Contains:
                - student_profile: dict with structured profile (no free-text)
                - model_one_output: dict with extracted info from Model 1
                - eligible_options: list of RecommendationOption (id, name, description, ...)
                - recommendation_type: "secondary_branch" or "university_major"

        Returns:
            ModelTwoOutput with:
                - recommendations: list of RankedRecommendation
                    Each must have: option_id (from eligible_options), rank, reasoning
                    Optional: score (0.0-1.0), extra metadata
                - metadata: optional dict with model info, processing time, etc.
                - success: bool
                - error: str or None if failed

        Raises:
            This method should not raise exceptions. Return success=False with error message instead.
        """
        # TODO(Oumnia): Implement the actual AI prompt logic here.
        # 1. Construct prompt from:
        #    - input_data.student_profile (structured academic data)
        #    - input_data.model_one_output (extracted insights from free text)
        #    - input_data.eligible_options (the options to rank)
        #    - input_data.recommendation_type (context for prompt)
        # 2. Call your chosen model
        # 3. Parse response into list of RankedRecommendation
        #    CRITICAL: Every option_id MUST be from input_data.eligible_options
        # 4. Return ModelTwoOutput with recommendations, metadata, success=True
        # 5. On failure, return ModelTwoOutput(success=False, error="...")

        # Placeholder - replace with actual implementation
        return ModelTwoOutput(
            success=False,
            error="Model 2 not yet implemented. Oumnia to implement rank() method.",
            recommendations=[],
            metadata={},
        )


# Convenience function for direct use if preferred
def rank_recommendations(input_data: ModelTwoInput) -> ModelTwoOutput:
    """Standalone function wrapper for Model 2 ranking.

    Can be used instead of the class if preferred.
    """
    client = ModelTwoClient()
    return client.rank(input_data)


class ModelTwoError(Exception):
    """Raised when Model 2 processing fails (for orchestrator to catch)."""

    pass