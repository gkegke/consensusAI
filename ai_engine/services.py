import logging
import instructor
from litellm import completion
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class StructuredAIResponse(BaseModel):
    score: float | None = Field(
        default=None,
        ge=0.0, 
        le=100.0, 
        description="Normalized sentiment score from 0.0 to 100.0. Use ONLY for SLIDER questions."
    )
    selected_choice: str | None = Field(
        default=None,
        description="The exact text of the chosen option. Use ONLY for MULTIPLE_CHOICE questions."
    )
    summary_sentence: str = Field(
        ..., 
        description="A concise, one-sentence summary of the model's stance."
    )
    is_refusal: bool = Field(
        default=False, 
        description="Set to true if the model refuses to answer due to alignment/safety filters."
    )
    refusal_reason: str = Field(
        default="", 
        description="If is_refusal is true, explain why."
    )

class AIOrchestratorService:
    @staticmethod
    def query_model(model_identifier: str, prompt: str) -> StructuredAIResponse:
        client = instructor.from_litellm(completion)
        
        try:
            response = client.chat.completions.create(
                model=model_identifier,
                messages=[
                    {"role": "system", "content": "You are an analytical sentiment engine. Adhere exactly to requested output structures."},
                    {"role": "user", "content": prompt}
                ],
                response_model=StructuredAIResponse,
                max_retries=2
            )
            return response
            
        except Exception as e:
            logger.error(f"AI Service Error for {model_identifier}: {str(e)}")
            return StructuredAIResponse(
                summary_sentence="System error during synthesis or format validation failed.", 
                is_refusal=True, 
                refusal_reason=str(e)
            )