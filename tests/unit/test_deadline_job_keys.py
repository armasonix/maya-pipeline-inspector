from __future__ import annotations

from pipeline_inspector.integrations.deadline.job_keys import (
    pass_label_from_job,
    scene_path_hint_from_job,
    shot_key_from_job,
)


def test_shot_key_and_pass_label_from_job_name():
    payload = {
        "_id": "job-1",
        "Name": "show_seq010_sh010_beauty_v02",
    }
    assert shot_key_from_job(payload) == "show_seq010_sh010"
    assert pass_label_from_job(payload) == "beauty"


def test_pass_label_detects_matte_tokens():
    payload = {"_id": "job-2", "Name": "show_seq010_sh010_matte_holdout"}
    assert pass_label_from_job(payload) == "matte"


def test_scene_path_hint_from_extra_info():
    payload = {
        "_id": "job-3",
        "ExtraInfo0": "D:/show/seq010/sh010/show_seq010_sh010.ma",
    }
    assert scene_path_hint_from_job(payload) == "D:/show/seq010/sh010/show_seq010_sh010.ma"
