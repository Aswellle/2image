import auto_build


def test_installer_template_renders_versioned_paths_and_shortcut():
    version = auto_build.get_version()
    script = auto_build.render_installer_script(version)

    assert f"AppVersion={version}" in script
    assert f"OutputBaseFilename=2image-setup-v{version}" in script
    assert f'OutputDir="{auto_build.INSTALLER_OUTPUT_DIR}"' in script
    assert "2image.exe\"; DestDir: \"{app}\"; Flags: ignoreversion" in script
    assert "2image_updater.exe\"; DestDir: \"{app}\"" in script
    assert "Name: \"{userdesktop}\\2image\"" in script
    assert "Tasks: desktopicon" in script
    assert "{APP_VERSION}" not in script
    assert "{OUTPUT_DIR}" not in script


def test_fixed_appid_keeps_legacy_install_identity():
    """The rename to 2image must NOT fork the install instance: the
    AppId stays pinned to the value derived from the old AppName."""
    script = auto_build.render_installer_script(auto_build.get_version())
    assert "AppId=text2image_pro" in script
    assert "AppName=2image" in script
