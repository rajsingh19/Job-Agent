from app.schemas.application_draft import QuestionCategory
from app.services.applications.question_classifier import QuestionClassifier


def test_classify_work_authorization_questions():
    questions = [
        "Are you legally authorized to work in the United States?",
        "Will you now or in the future require visa sponsorship for employment?",
        "What is your current work authorization status (H1B, OPT, CPT, Citizen)?",
    ]
    for q in questions:
        assert QuestionClassifier.classify(q) == QuestionCategory.WORK_AUTHORIZATION


def test_classify_salary_and_availability():
    assert (
        QuestionClassifier.classify("What is your expected salary range for this role?")
        == QuestionCategory.SALARY
    )
    assert (
        QuestionClassifier.classify("What is your desired compensation / monthly stipend?")
        == QuestionCategory.SALARY
    )
    assert (
        QuestionClassifier.classify("When can you start if an offer is extended?")
        == QuestionCategory.AVAILABILITY
    )
    assert (
        QuestionClassifier.classify("What is your notice period with your current employer?")
        == QuestionCategory.AVAILABILITY
    )


def test_classify_motivation_and_fit():
    assert (
        QuestionClassifier.classify("Why do you want to work at our company?")
        == QuestionCategory.MOTIVATION
    )
    assert (
        QuestionClassifier.classify("Why are you the best fit for this software engineering position?")
        == QuestionCategory.ROLE_FIT
    )


def test_classify_technical_and_education():
    assert (
        QuestionClassifier.classify("Describe a challenging technical project you built.")
        == QuestionCategory.PROJECT
    )
    assert (
        QuestionClassifier.classify("What is your level of proficiency in React and TypeScript?")
        == QuestionCategory.SKILL
    )
    assert (
        QuestionClassifier.classify("What is your expected graduation year from university?")
        == QuestionCategory.EDUCATION
    )
    assert (
        QuestionClassifier.classify("How many years of professional software engineering experience do you have?")
        == QuestionCategory.EXPERIENCE
    )
    assert (
        QuestionClassifier.classify("Tell me about a time you handled conflict on an engineering team.")
        == QuestionCategory.BEHAVIORAL
    )
