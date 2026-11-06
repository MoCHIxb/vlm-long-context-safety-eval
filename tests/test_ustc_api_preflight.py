import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ustc_preflight", ROOT / "scripts/check_ustc_api.py")
API = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(API)


class USTCPreflightTest(unittest.TestCase):
    def setUp(self):
        self.config = {"base_url": "https://api.llm.ustc.edu.cn/v1", "model": "deepseek-flash-2",
                       "api_key_env": "USTC_LLM_API_KEY", "probe_max_tokens": 64}

    def test_other_destination_rejected_before_reading_secret_or_sending(self):
        self.config["base_url"] = "https://example.com/v1"
        with patch.object(API.os.environ, "get") as secret, patch.object(API.urllib.request, "build_opener") as network:
            with self.assertRaises(ValueError):
                API.request_json(self.config, "/models")
            secret.assert_not_called()
            network.assert_not_called()

    def test_missing_key_never_sends_request(self):
        with patch.dict(API.os.environ, {"USTC_LLM_API_KEY": ""}), patch.object(API.urllib.request, "build_opener") as network:
            with self.assertRaises(ValueError):
                API.request_json(self.config, "/models")
            network.assert_not_called()

    def test_listing_does_not_silently_switch_to_a_different_model(self):
        with patch.object(API, "request_json", return_value={"data": [{"id": "different-model"}]}):
            result = API.run(self.config, smoke=False)
        self.assertFalse(result["requested_model_listed"])
        self.assertEqual(result["requested_model"], "deepseek-flash-2")

    def test_probe_contains_only_a_benign_request_and_bounded_output(self):
        answer = {"model": "backend-name", "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}]}
        with patch.object(API, "request_json", return_value=answer) as send:
            result = API.run(self.config, smoke=True)
        payload = send.call_args.args[2]
        self.assertEqual(payload["messages"], [{"role": "user", "content": "Reply with exactly OK."}])
        self.assertEqual(payload["max_tokens"], 64)
        self.assertEqual(result["returned_model"], "backend-name")
        self.assertTrue(result["response_received"])

    def test_vision_payload_contains_images_without_text_color_hints(self):
        payload = API.vision_payload(self.config, ["red", "blue", "green"])
        content = payload["messages"][0]["content"]
        self.assertEqual(len(content), 4)
        self.assertTrue(all(c["image_url"]["url"].startswith("data:image/png;base64,") for c in content[1:]))
        for name in ("red", "blue", "green"):
            self.assertNotIn(name, content[0]["text"].lower())

    def test_vision_mismatch_does_not_claim_image_support(self):
        answer = {"choices": [{"message": {"content": '{"unavailable":true}'}, "finish_reason": "stop"}]}
        with patch.object(API, "request_json", return_value=answer):
            result = API.run_vision(self.config)
        self.assertFalse(result["matched"])
        self.assertEqual(result["dataset_files_read"], 0)
        self.assertFalse(result["gpu_used"])


if __name__ == "__main__":
    unittest.main()
