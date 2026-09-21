# NIR Intelligence Platform - Chatbot API URLs (roadmap S6)
# URL routing for the result discussion chatbot endpoints

from django.urls import include, path

from .chatbot_views import chatbot_message, chatbot_status

urlpatterns = [
    path("message/", chatbot_message, name="chatbot_message"),
    path("status/", chatbot_status, name="chatbot_status"),
]

chatbot_api_urls = [path("api/chatbot/", include(urlpatterns))]
chatbot_urls = urlpatterns
