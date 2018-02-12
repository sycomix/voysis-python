import requests
from furl import furl
from requests import HTTPError
from requests.packages.urllib3.exceptions import HTTPError as UrlLib3HTTPError

from voysis.client import client as client


class HTTPClient(client.Client):

    def __init__(self, url, user_agent=None):
        client.Client.__init__(self, url, user_agent)
        self.base_url = furl(url)

    def send_request(self, uri, request_entity=None, extra_headers=None, call_on_complete=None):
        headers = self.create_common_headers()
        if extra_headers:
            headers.update(extra_headers)
        url = self.base_url.copy().add(path=uri)
        response = requests.post(
            str(url),
            headers=headers,
            json=request_entity
        )
        return client.ResponseFuture(
            response_code=response.status_code,
            response_entity=response.json(),
            call_on_complete=call_on_complete
        )

    def stream_audio(self, frames_generator, notification_handler=None):
        try:
            self.refresh_app_token()
            conversation_id = self.current_conversation_id if self.current_conversation_id else '*'
            headers = self.create_common_headers()
            headers['Content-Type'] = 'audio/wav'
            headers['Accept-Language'] = self.locale
            streaming_url = self.base_url.copy().add(
                path=['conversations', conversation_id, 'queries', '*', 'audio']
            )
            response = requests.post(
                str(streaming_url),
                headers=headers,
                stream=True,
                data=frames_generator
            )
            if response.status_code == 200:
                query = response.json()
                self.current_conversation_id = query['conversationId']
                self._update_current_context(query)
                return query
            else:
                raise client.ClientError('Request failed with status code {}'.format(response.status_code))
        except OSError as error:
            msg = error.strerror
            if not msg:
                msg = str(error)
            raise client.ClientError(msg)
        except (HTTPError, UrlLib3HTTPError) as error:
            raise client.ClientError(str(error))
        except Exception as error:
            print(type(error))
