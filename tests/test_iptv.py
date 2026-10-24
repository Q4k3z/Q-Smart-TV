import pytest
from core.iptv_service import iptv_service

SAMPLE_M3U = """#EXTM3U
#EXTINF:-1 tvg-id="vtv1" tvg-name="VTV1" group-title="Quốc Gia",VTV1 HD
https://example.com/live/vtv1.m3u8
#EXTINF:-1 tvg-id="vtv3" tvg-name="VTV3" group-title="Giải Trí",VTV3 HD
https://example.com/live/vtv3.m3u8
"""

def test_iptv_parse_local_m3u(tmp_path):
    m3u_file = tmp_path / "test_channels.m3u"
    m3u_file.write_text(SAMPLE_M3U, encoding="utf-8")

    channels = iptv_service.load_channels(url=str(m3u_file))
    assert len(channels) == 2
    assert channels[0]["title"] == "VTV1 HD"
    assert channels[0]["url"] == "https://example.com/live/vtv1.m3u8"
    assert channels[1]["title"] == "VTV3 HD"

def test_playlist_management():
    # Add playlist
    new_pl = iptv_service.add_playlist("Kênh Gia Đình", "https://example.com/family.m3u")
    assert new_pl["name"] == "Kênh Gia Đình"
    p_id = new_pl["id"]

    # Verify list
    playlists = iptv_service.get_playlists()
    assert any(p["id"] == p_id for p in playlists)

    # Delete playlist
    deleted = iptv_service.delete_playlist(p_id)
    assert deleted is True

def test_favorite_toggle():
    test_ch = {"title": "Test Channel", "url": "https://example.com/test.m3u8"}
    
    # Add to favorite
    added = iptv_service.toggle_favorite(test_ch)
    assert added is True
    favs = iptv_service.get_favorites()
    assert any(f["url"] == test_ch["url"] for f in favs)

    # Remove from favorite
    removed = iptv_service.toggle_favorite(test_ch)
    assert removed is False


def test_all_channels_combines_configured_playlists(tmp_path, monkeypatch):
    first = tmp_path / 'first.m3u'
    second = tmp_path / 'second.m3u'
    first.write_text(SAMPLE_M3U, encoding='utf-8')
    second.write_text(SAMPLE_M3U, encoding='utf-8')
    monkeypatch.setattr(iptv_service, 'get_playlists', lambda: [
        {'id':'one','url':str(first)}, {'id':'two','url':str(second)}])
    assert len(iptv_service.load_channels()) == 4


def test_playlist_names_do_not_cause_id_collisions():
    first = iptv_service.add_playlist('Kênh gia đình', 'https://example.com/a.m3u')
    second = iptv_service.add_playlist('Kênh gia đình', 'https://example.com/b.m3u')
    try:
        assert first['id'] != second['id']
    finally:
        iptv_service.delete_playlist(first['id'])
        iptv_service.delete_playlist(second['id'])
