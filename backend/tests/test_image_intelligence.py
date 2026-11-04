from app.services.image_intelligence import contrast_ratio, delta_e_2000

def test_contrast_ratio_known_values():
    assert round(contrast_ratio('#000000','#FFFFFF'),2)==21.0

def test_ciede2000_same_color_and_distance():
    assert delta_e_2000('#FFFFFF','#FFFFFF') < 0.01
    assert delta_e_2000('#FFFFFF','#000000') > 50
