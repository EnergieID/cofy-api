from cofy.modules.members import MembersCSVSource


def test_members_csv_source_loads_members_filters_by_email_and_verifies_activation_codes(tmp_path):
    csv_path = tmp_path / "members.csv"
    csv_path.write_text("id,email,activation_code\n1,a@example.com,code-a\n2,b@example.com,\n3,,code-c\n")

    source = MembersCSVSource(
        str(csv_path),
        id_field="id",
        email_field="email",
        activation_code_field="activation_code",
    )

    members = source.list()
    assert [member.id for member in members] == ["1", "2", "3"]
    assert [member.email for member in members] == ["a@example.com", "b@example.com", ""]

    filtered_members = source.list(email="a@example.com")
    assert [member.id for member in filtered_members] == ["1"]
    assert source.list(email="missing@example.com") == []

    assert source.verify("code-a") == members[0]
    assert source.verify("code-c") == members[2]
    assert source.verify("missing") is None


def test_members_csv_source_handles_missing_optional_columns(tmp_path):
    csv_path = tmp_path / "members.csv"
    csv_path.write_text("id\n1\n2\n")

    source = MembersCSVSource(str(csv_path), id_field="id")

    members = source.list()
    assert [member.id for member in members] == ["1", "2"]
    assert [member.email for member in members] == [None, None]
    assert source.verify("any-code") is None
