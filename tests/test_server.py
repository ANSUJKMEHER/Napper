import json
import socketserver
import threading
import urllib.request

from napper import server


def test_server_stored_datasets():
    datasets = server.get_stored_datasets()
    assert isinstance(datasets, list)
    assert len(datasets) >= 3
    names = [d["name"] for d in datasets]
    assert "bank" in names
    assert "electricity" in names
    assert "steps" in names


def test_server_chart_data():
    chart_data = server.get_series_chart_data("electricity:kwh")
    assert "series_name" in chart_data
    assert "model" in chart_data
    assert "history" in chart_data
    assert isinstance(chart_data["history"], list)
    assert "anomalies" in chart_data
    assert "forecast" in chart_data


def test_server_http_endpoints():
    class TestServer(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = TestServer(("127.0.0.1", 0), server.NapperRequestHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        # Test index.html
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "Napper" in content

        # Test /api/status
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ready"
            assert "datasets" in data

        # Test /api/chart
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/chart?series=electricity:kwh") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["series_name"] == "electricity:kwh"
    finally:
        httpd.shutdown()
        httpd.server_close()

