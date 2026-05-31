from .models import PersonaProfile


PERSONA_BUSY_MOM = PersonaProfile(
    name="Busy Mom",
    age=38,
    tech_savviness=2,
    attention_span_seconds=45,
    motivation_level=3,
    cognitive_biases=["loss aversion", "status quo bias"],
)

PERSONA_TECH_MILLENNIAL = PersonaProfile(
    name="Tech Millennial",
    age=28,
    tech_savviness=5,
    attention_span_seconds=120,
    motivation_level=4,
    cognitive_biases=["social proof"],
)

PERSONA_SENIOR_SHOPPER = PersonaProfile(
    name="Senior Shopper",
    age=62,
    tech_savviness=1,
    attention_span_seconds=90,
    motivation_level=5,
    cognitive_biases=["authority bias", "anchoring"],
)
