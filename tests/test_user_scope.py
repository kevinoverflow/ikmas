from app.backend.user_scope import sanitize_workspace_part, user_workspace_id


def test_user_workspace_id_scopes_default_collection_by_user():
    first = user_workspace_id("11111111-1111-1111-1111-111111111111")
    second = user_workspace_id("22222222-2222-2222-2222-222222222222")

    assert first == "u_11111111-1111-1111-1111-111111111111__default"
    assert second == "u_22222222-2222-2222-2222-222222222222__default"
    assert first != second


def test_user_workspace_id_preserves_logical_collection_inside_user_scope():
    workspace_id = user_workspace_id("user-1", "team notes")

    assert workspace_id == "u_user-1__team_notes"


def test_user_workspace_id_compacts_long_values_for_chroma():
    workspace_id = user_workspace_id("user-" + "x" * 80, "collection-" + "y" * 80)

    assert len(workspace_id) <= 63
    assert workspace_id.startswith("u_user-")
    assert workspace_id[-1].isalnum()


def test_sanitize_workspace_part_rejects_path_separators():
    assert sanitize_workspace_part("../other-user") == "other-user"
    assert sanitize_workspace_part("team/notes") == "team_notes"
