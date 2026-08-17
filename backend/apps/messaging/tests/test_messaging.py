"""Basic tests for the Messaging module."""

from rest_framework.test import APITestCase

from apps.accounts.models import Role, User


class MessagingBaseTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_role, _ = Role.objects.get_or_create(
            name="cj_admin", defaults={"is_system": True, "is_frozen": True}
        )
        cls.sme_role, _ = Role.objects.get_or_create(
            name="sme", defaults={"is_system": True, "is_frozen": True}
        )
        cls.admin = User.objects.create_user(
            email="admin@msg-test.com", password="pw12345", is_active=True, role=cls.admin_role
        )
        cls.sme = User.objects.create_user(
            email="sme@msg-test.com", password="pw12345", is_active=True, role=cls.sme_role
        )


class MessageTests(MessagingBaseTestCase):
    def test_send_message(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/messaging/messages/",
            {"recipient": self.admin.id, "subject": "Hello", "body": "Test message"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_list_own_messages(self):
        self.client.force_authenticate(self.sme)
        # Send a message first
        self.client.post(
            "/api/messaging/messages/",
            {"recipient": self.admin.id, "body": "Hi"},
            format="json",
        )
        resp = self.client.get("/api/messaging/messages/")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_reply_to_message(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/messaging/messages/",
            {"recipient": self.admin.id, "body": "Original"},
            format="json",
        )
        msg_id = resp.json()["data"]["id"]
        # Admin replies
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/messaging/messages/{msg_id}/reply/",
            {"body": "Reply text"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_mark_read(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/messaging/messages/",
            {"recipient": self.admin.id, "body": "Read me"},
            format="json",
        )
        msg_id = resp.json()["data"]["id"]
        self.client.force_authenticate(self.admin)
        resp = self.client.patch(f"/api/messaging/messages/{msg_id}/mark_read/")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_contacts_list(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.get("/api/messaging/conversations/contacts/")
        self.assertEqual(resp.status_code, 200, resp.content)
        contacts = resp.json()["data"]
        # SME should see cj_admin in contacts
        self.assertTrue(any(c["role__name"] == "cj_admin" for c in contacts))


class ConversationTests(MessagingBaseTestCase):
    def test_list_conversations(self):
        self.client.force_authenticate(self.sme)
        # Send a message to create a conversation
        self.client.post(
            "/api/messaging/messages/",
            {"recipient": self.admin.id, "body": "Start conversation"},
            format="json",
        )
        resp = self.client.get("/api/messaging/conversations/")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_view_thread(self):
        self.client.force_authenticate(self.sme)
        resp = self.client.post(
            "/api/messaging/messages/",
            {"recipient": self.admin.id, "body": "Thread msg"},
            format="json",
        )
        # Get conversations
        resp = self.client.get("/api/messaging/conversations/")
        results = resp.json().get("results", resp.json().get("data", []))
        if results:
            conv_id = results[0]["id"]
            resp = self.client.get(f"/api/messaging/conversations/{conv_id}/thread/")
            self.assertEqual(resp.status_code, 200, resp.content)
