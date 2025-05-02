import requests
import json
from typing import Dict


class LLM:
    """
    此类用于通过HTTP请求与大型语言模型（LLM）进行交互。
    """

    def __init__(
        self,
        url: str,
        model_name: str = "Zephyr",
        api_key: str = "",
        history_length: int = 5,
        mask: str = "You are a helpful assistant.",
        stream: bool = False,
    ):
        """
        初始化LLM类实例。

        :param url: LLM服务的URL。
        :param model_name: 使用的模型名称，默认为 'Zephyr'。
        :param api_key: 用于API认证的密钥。
        :param history_length: 对话历史长度，决定保留多少轮对话。
        :param mask: 系统角色的默认提示。
        :param stream: 是否开启流式响应。
        """
        self.url = url
        self.model = model_name
        self.history_length = history_length
        self.history = []
        self.mask = mask
        self.stream = stream
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "text/event-stream" if self.stream else "application/json",
        }

    def __call__(self, prompt: str) -> str:
        """
        发送提示至LLM并返回响应。

        :param prompt: 用户输入。
        :return: LLM的响应。
        """
        if self.history_length != 0:
            return (
                self._send_stream(self._update_history(prompt))
                if self.stream
                else self._send_request(self._update_history(prompt))
            )

        return (
            self._send_stream(self._create_message(prompt))
            if self.stream
            else self._send_request(self._create_message(prompt))
        )

    def _create_message(self, prompt: str) -> Dict:
        """
        创建不带历史管理的新消息。

        :param prompt: 用户输入。
        :return: 新消息字典。
        """
        return (
            {
                "messages": [
                    {"role": "system", "content": f"{self.mask}"},
                    {"role": "user", "content": prompt},
                ],
                "model": self.model,
                "stream": self.stream,
            }
            if self.mask
            else {
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "model": self.model,
                "stream": self.stream,
            }
        )

    def _send_request(self, msg: Dict) -> str:
        """
        向LLM发送请求的辅助方法。

        :param msg: 要发送的消息字典。
        :return: LLM的响应或错误信息。
        """
        try:
            response = requests.post(self.url, headers=self.headers, json=msg)
            response.raise_for_status()
            res_text = response.json()["choices"][0]["message"]["content"]
            if self.history_length != 0:
                self.history.append({"role": "assistant", "content": res_text})
            return res_text
        except requests.RequestException as e:
            return f"发生错误：{e}"
        except KeyError as e:
            return f"返回错误：{response.json()}"

    def _send_stream(self, msg: Dict) -> str:
        try:
            response = requests.post(
                self.url, headers=self.headers, json=msg, stream=True
            )
            response.raise_for_status()

            res_text = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8")
                    # 移除前缀 'data: ' 获取JSON字符串
                    json_str = decoded_line[len("data: ") :]
                    try:
                        if json_str.startswith("{"):
                            json_data = json.loads(json_str)
                            delta = json_data["choices"][0]["delta"]
                            if "content" in delta:
                                res_text += delta["content"]
                                yield delta["content"]
                        else:
                            yield "\n"
                    except json.JSONDecodeError as e:
                        print("解析JSON时发生错误：", e)

            self.history.append({"role": "assistant", "content": res_text})
        except requests.RequestException as e:
            yield f"发生错误：{e}"

    def _update_history(self, prompt: str) -> Dict:
        """
        更新对话历史。

        :param prompt: 用户输入。
        :return: 更新后的消息字典。
        """
        if len(self.history) > 2 * self.history_length:
            self.history = self.history[-(2 * self.history_length) :]
        self.history.append({"role": "user", "content": prompt})
        return (
            {
                "messages": [{"role": "system", "content": f"{self.mask}"}]
                + self.history,
                "model": self.model,
                "stream": self.stream,
            }
            if self.mask
            else {
                "messages": self.history,
                "model": self.model,
                "stream": self.stream,
            }
        )

    def reset(self):
        """
        重置对话历史和摘要。
        """
        self.history = []
