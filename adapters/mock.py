from src.runner import (
    ModelAdapter,
    ModelResponse,
)


class SafeMockModel(ModelAdapter):

    def generate(
        self,
        messages,
        tools=None,
    ):

        return ModelResponse(
            text=(
                "I can't provide private information "
                "that the requester is not authorized to access."
            )
        )


class LeakyMockModel(ModelAdapter):

    def generate(
        self,
        messages,
        tools=None,
    ):

        return ModelResponse(
            text=(
                "The requested private information is "
                "42 Oak Street, Portland."
            )
        )

