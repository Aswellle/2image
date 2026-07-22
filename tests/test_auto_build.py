import auto_build


def test_installer_template_renders_versioned_paths_and_shortcut():
    version = auto_build.get_version()
    script = auto_build.render_installer_script(version)

    assert f"AppVersion={version}" in script
    assert f"OutputBaseFilename=text2image_pro_v{version}" in script
    assert f'OutputDir="{auto_build.INSTALLER_OUTPUT_DIR}"' in script
    assert "text2image_pro.exe\"; DestDir: \"{app}\"; Flags: ignoreversion" in script
    assert "Name: \"{userdesktop}\\text2image_pro\"" in script
    assert "Tasks: desktopicon" in script
    assert "{APP_VERSION}" not in script
    assert "{OUTPUT_DIR}" not in script
