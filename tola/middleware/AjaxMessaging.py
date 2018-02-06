import json

from django.contrib import messages


class AjaxMessaging(object):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_response(self, request, response):
        if request.is_ajax():
            print("ajax done: %s" % response['Content-Type'])
            if response['Content-Type'] in ["application/javascript", "application/json"]:
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
                if type(content) == list:
                    content = {"data" : content}
                content['django_messages'] = django_messages

                response.content = json.dumps(content)
        return response
