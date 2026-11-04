from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password('safe-password-123')
    second = hash_password('safe-password-123')
    assert first != second
    assert verify_password('safe-password-123', first)
    assert not verify_password('wrong-password', first)


def test_access_token_contains_workspace_and_role() -> None:
    token = create_access_token('user-1', 'workspace-1', 'admin')
    claims = decode_access_token(token)
    assert claims['sub'] == 'user-1'
    assert claims['workspace_id'] == 'workspace-1'
    assert claims['role'] == 'admin'
