def test_validation_location_yaml_path():
    from workflow_validator.models.location import ValidationLocation

    location = ValidationLocation(
        file_path="workflow.yaml",
        line=42,
        column=15,
        yaml_path="actions.SendEmail.properties.to",
        context_lines=["    properties:", "      to: []", "      subject: Alert"]
    )

    assert location.get_friendly_path() == "actions → SendEmail → properties → to"
    assert location.has_context() == True
    assert len(location.context_lines) == 3