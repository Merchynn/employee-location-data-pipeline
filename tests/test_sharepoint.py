from employee_location_pipeline.config import SharePointSettings, SourceSettings
from employee_location_pipeline.extract import SharePointExcelClient


def test_shared_link_uses_graph_shares_endpoint():
    settings = SourceSettings(
        mode="sharepoint",
        sharepoint=SharePointSettings(
            share_url="https://contoso.sharepoint.com/:x:/s/PeopleAnalytics/example"
        ),
    )
    url = SharePointExcelClient(settings)._download_url()
    assert "/shares/u!" in url
    assert url.endswith("/driveItem/content")
