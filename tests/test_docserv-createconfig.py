import pytest
from docserv_createconfig import get_origin_url, get_version

@pytest.mark.parametrize("path, url",
    [("/home/eroca/Documents/docserv-project/docserv-config", "https://gitlab.suse.de/susedoc/docserv-config.git"),
    (os.getcwd().replace("/bin", ""), "https://github.com/openSUSE/docserv.git"),
    ("../../../docserv-project_old/docserv-config", "https://gitlab.suse.de/susedoc/docserv-config.git"),
])
def test_get_origin_url(path, url):
    assert get_origin_url(path) == url

@pytest.mark.parametrize("name, version",
    [("SLE12", "12"),
    ("SLE12SP4", "12 SP4"),
    ("openSUSE_Leap_15.0", "15.0"),
    ("develop", "develop"),
])
def test_get_version(name, version):
    assert get_version(name) == version
