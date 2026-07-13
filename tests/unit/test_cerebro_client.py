from __future__ import annotations

from dataclasses import dataclass, field

from pipeline_inspector.integrations.cerebro import CerebroClient, CerebroConfig
from pipeline_inspector.integrations.cerebro.client import format_note_html


@dataclass
class FakeCerebroDatabase:
    connected: bool = False
    credentials: tuple[str, str] = ("", "")
    task_urls: dict[str, int] = field(default_factory=dict)
    definition_message_ids: dict[int, int] = field(default_factory=dict)
    notes: list[tuple[int, int, str]] = field(default_factory=list)
    next_message_id: int = 100

    def connect(self, user: str, password: str) -> bool:
        self.connected = True
        self.credentials = (user, password)
        return True

    def task_by_url(self, task_url: str) -> int | None:
        return self.task_urls.get(task_url)

    def task_definition_message_id(self, task_id: int) -> int | None:
        return self.definition_message_ids.get(task_id)

    def add_note(self, task_id: int, parent_message_id: int, html_text: str) -> int | None:
        self.notes.append((task_id, parent_message_id, html_text))
        message_id = self.next_message_id
        self.next_message_id += 1
        return message_id


def test_cerebro_client_ping_connects_with_credentials():
    database = FakeCerebroDatabase()
    client = CerebroClient(
        CerebroConfig(
            server_url="cerebrohq.com:45432",
            api_user="pipeline.bot",
            api_password="secret",
            project="Demo Project",
        ),
        database_port=database,
    )

    assert client.ping() is True
    assert database.credentials == ("pipeline.bot", "secret")


def test_cerebro_client_create_task_note_posts_html_note():
    database = FakeCerebroDatabase(
        definition_message_ids={42: 7},
    )
    client = CerebroClient(
        CerebroConfig(
            server_url="cerebrohq.com",
            api_user="pipeline.bot",
            api_password="secret",
            project="Demo Project",
        ),
        database_port=database,
    )

    note = client.create_task_note(task_id=42, content="Pipeline Inspector summary\nline 2")

    assert note == {"id": 100, "task_id": 42}
    assert database.notes == [(42, 7, "Pipeline Inspector summary<br/>line 2")]


def test_format_note_html_escapes_markup():
    assert format_note_html("<b>warn</b>\nnext") == "&lt;b&gt;warn&lt;/b&gt;<br/>next"
