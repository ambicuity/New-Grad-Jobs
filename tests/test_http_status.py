from update_jobs import is_retryable_status

class TestIsRetryableStatus:
    def test_404_not_retryable(self):
        assert is_retryable_status(404) is False

    def test_403_retryable(self):
        assert is_retryable_status(403) is True

    def test_429_retryable(self):
        assert is_retryable_status(429) is True

    def test_500_retryable(self):
        assert is_retryable_status(500) is True

    def test_502_retryable(self):
        assert is_retryable_status(502) is True

    def test_503_retryable(self):
        assert is_retryable_status(503) is True

    def test_504_retryable(self):
        assert is_retryable_status(504) is True

    def test_400_not_retryable(self):
        assert is_retryable_status(400) is False

    def test_401_not_retryable(self):
        assert is_retryable_status(401) is False

    def test_200_not_retryable(self):
        assert is_retryable_status(200) is False

    def test_unknown_5xx_retryable(self):
        assert is_retryable_status(599) is True

    def test_unknown_4xx_not_retryable(self):
        assert is_retryable_status(418) is False
