import json

from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages


class AjaxMessaging(MiddlewareMixin):

    def process_response(self, request, response):
        if request.is_ajax():
            if response['Content-Type'] in ["application/javascript",
                                            "application/json"]:
                try:
                    content = json.loads(response.content)
                except ValueError as e:
                    print("Error has occured: %s" % e)
                    return response

                django_messages = []

                for message in messages.get_messages(request):
                    django_messages.append({
                        "level": message.level,
                        "message": message.message,
                        "extra_tags": message.tags,
                    })

                # workaround for list type data
                if isinstance(content, list):
                    content = {"data": content}
                content['django_messages'] = django_messages

                response.content = json.dumps(content)
        return response
