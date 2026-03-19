import logging
import instructor
import litellm
from litellm import completion, completion_cost
from pydantic import BaseModel, Field
from typing import List, Optional

# Silencing LiteLLM for Python 3.12 
litellm.telemetry = False
litellm.set_verbose = False

logger = logging.getLogger(__name__)

class ChoiceProbability(BaseModel):
    choice: str = Field(..., description="The name of the outcome (Seed option or AI-discovered Dark Horse).")
    confidence: float = Field(..., ge=0, le=100, description="Probability percentage. Must sum to 100 with others.")

class BaseStructuredResponse(BaseModel):
    summary_sentence: str = Field(..., description="Concise stance summary. Explain inclusion of high probability dark horses.")
    is_refusal: bool = Field(default=False, description="True if safety filters blocked answer.")
    refusal_reason: str = Field(default="")

class SliderResponse(BaseStructuredResponse):
    score: float = Field(..., ge=0, le=100)

class BinaryResponse(BaseStructuredResponse):
    score: float = Field(..., ge=0, le=100)

class ChoiceResponse(BaseStructuredResponse):
    complex_forecast: List[ChoiceProbability] = Field(..., min_items=1, max_items=12)

class SynthesisResponse(BaseModel):
    synthesis_summary: str = Field(..., description="Summary of collective consensus.")
    minority_report: str = Field(..., description="Summary of dissenting views.")
    polarization_index: float = Field(..., ge=0, le=100)

class AIOrchestratorService:
    @staticmethod
    def safe_get_cost(completion_obj) -> float:
        try:
            return completion_cost(completion_obj)
        except Exception:
            return 0.0

    @staticmethod
    def query_model(model_obj, question) -> tuple[Optional[dict], float]:
        client = instructor.from_litellm(completion)
        
        # Mapping schemas
        mapping = {
            'SUBJECTIVE_SLIDER': SliderResponse,
            'PREDICTIVE_BINARY': BinaryResponse,
            'PREDICTIVE_CHOICE': ChoiceResponse,
        }
        schema = mapping.get(question.question_type, SliderResponse)
        
        system_msg = "You are a world-class forecasting engine and strategic analyst."
        
        user_prompt = f"QUESTION: {question.text}\nCONTEXT: {question.context}\n"
        
        if question.question_type == 'PREDICTIVE_CHOICE':
            seed_list = ", ".join(question.choices) if question.choices else "None provided"
            user_prompt += (
                f"COMMUNITY SEED LIST: [{seed_list}]\n\n"
                "INSTRUCTIONS:\n"
                "1. The Seed List may be biased, incomplete, or contain 'lazy' omissions.\n"
                "2. Evaluate the Seed List, but DO NOT be restricted by it.\n"
                "3. Identify and include 'Dark Horse' candidates or omitted high-probability outcomes (>1% chance).\n"
                "4. Distribute 100% probability across the most likely outcomes (max 10 total - allocating the rest as Other).\n"
            )
        else:
            user_prompt += "Provide a precise 0-100 score representing your confidence or stance."

        try:
            logger.info(f"AI_QUERY_START | Model: {model_obj.api_identifier} | Q: {question.slug}")
            
            response, raw_completion = client.chat.completions.create_with_completion(
                model=model_obj.api_identifier,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt}
                ],
                response_model=schema,
                max_retries=2
            )
            return response.model_dump(), AIOrchestratorService.safe_get_cost(raw_completion)
        except Exception as e:
            logger.error(f"AI_QUERY_ERROR | {model_obj.api_identifier} | {str(e)}")
            return None, 0

    @staticmethod
    def synthesize_run(run) -> tuple[Optional[dict], float]:
        responses = run.responses.filter(is_refusal=False)
        if not responses.exists():
            return None, 0

        context_lines = []
        for r in responses:
            data = r.normalized_score if r.normalized_score is not None else r.complex_forecast
            context_lines.append(f"Model {r.model.name}: {data} | Summary: {r.summary_sentence}")
        
        payload = "\n".join(context_lines)
        
        try:
            client = instructor.from_litellm(completion)
            response, raw_completion = client.chat.completions.create_with_completion(
                model="gemini/gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": "Aggregate these model forecasts."},
                    {"role": "user", "content": f"Forecast Data:\n{payload}"}
                ],
                response_model=SynthesisResponse
            )
            return response.model_dump(), AIOrchestratorService.safe_get_cost(raw_completion)
        except Exception as e:
            logger.error(f"SYNTH_ERROR | {str(e)}")
            return None, 0