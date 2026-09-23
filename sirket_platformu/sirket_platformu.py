import reflex as rx
from .dashboard_view import dashboard_page
from .quote_builder import quote_builder_page
from .quote_state import QuoteState
from .dashboard_state import DashboardState
from .technical_scope_view import technical_scope_page
from .labor_engine_view import labor_engine_page
from .revision_diff_view import revision_diff_page
from .competitor_intel_view import competitor_intel_page
from .dynamic_pricing_view import dynamic_pricing_page
from .margin_simulator_view import margin_simulator_page
from .price_catalog_view import price_catalog_page
from .quote_upload_view import quote_upload_page
from .cost_upload_view import cost_upload_page
from .supplier_compare_view import supplier_compare_page
from .technical_scope_state import TechnicalScopeState
from .supplier_compare_state import SupplierCompareState


app = rx.App(
    theme=rx.theme(
        appearance="dark",
        has_background=True,
        accent_color="blue",
        radius="medium",
    ),
    style={
        "*:focus": {"outline": "none !important"},
        "svg:focus": {"outline": "none !important"},
        "path:focus": {"outline": "none !important"},
        ".recharts-surface:focus": {"outline": "none !important"},
        ".recharts-sector:focus": {"outline": "none !important"},
        ".recharts-pie:focus": {"outline": "none !important"},
    },
)

# Ana sayfa: Dashboard
app.add_page(
    dashboard_page,
    route="/",
    title="Dashboard (Analiz) | PetroTek",
    on_load=[
        QuoteState.set_active_module("Dashboard (Analiz)"),
        DashboardState.start_hourly_rate_scheduler,  # TCMB saatlik arka plan çekicisini başlatır
    ],
)

# Teklif Hazırlama Sayfası
app.add_page(
    quote_builder_page,
    route="/teklif-hazirla",
    title="Yeni Teklif Hazırla | PetroTek",
    on_load=QuoteState.set_active_module("Yeni Teklif Hazırla & Çıktı Al"),
)

# Teknik Teklif & Kapsam Dosyası Üreteci Sayfası
app.add_page(
    technical_scope_page,
    route="/teknik-kapsam",
    title="Teknik Kapsam Üreteci | PetroTek",
    on_load=QuoteState.set_active_module("Teknik Teklif & Kapsam Dosyası Üreteci"),
)

#Saha İşçilik & Montaj Sayfası
app.add_page(
    labor_engine_page,
    route="/iscilik-motoru",
    title="Saha İşçilik Motoru (A/S) | PetroTek",
    on_load=QuoteState.set_active_module("Saha İşçilik & Montaj Motoru (A/S)"),
)


#Revizyon Takibi Sayfası
app.add_page(
    revision_diff_page,
    route="/revizyon-takibi",
    title="Revizyon & Fark Takibi | PetroTek",
    on_load=QuoteState.set_active_module("Revizyon & Fark Takibi"),
)


#Rakip Fiyat Tahmini ve İstihbarat
app.add_page(
    competitor_intel_page,
    route="/rakip-istihbarat",
    title="Rakip Fiyat Tahmini & İstihbarat | PetroTek",
    on_load=QuoteState.set_active_module("Rakip Fiyat Tahmini & İstihbarat"),
)


#Dinamik Fiyatlandırma & Kazanma Tahmini
app.add_page(
    dynamic_pricing_page,
    route="/dinamik-fiyatlama",
    title="Dinamik Fiyatlama & Kazanma Tahmini | PetroTek",
    on_load=QuoteState.set_active_module("Dinamik Fiyatlama & Kazanma Tahmini"),
)


#Marj & İskonto Simülatörü
app.add_page(
    margin_simulator_page,
    route="/marj-simulatoru",
    title="Marj & İskonto Simülatörü | PetroTek",
    on_load=QuoteState.set_active_module("Marj & İskonto Simülatörü"),
)


#Fiyat Hafızası & Katalog
app.add_page(
    price_catalog_page,
    route="/fiyat-hafizasi",
    title="Fiyat Hafızası & Katalog | PetroTek",
    on_load=QuoteState.set_active_module("Fiyat Hafızası & Katalog"),
)


#Teklif Yükle
app.add_page(
    quote_upload_page,
    route="/teklif-yukle",
    title="Teklif Yükle (PDF / Excel) | PetroTek",
    on_load=QuoteState.set_active_module("Teklif Yükle (PDF / Excel)"),
)


#Maliyet Yükle
app.add_page(
    cost_upload_page,
    route="/maliyet-yukle",
    title="Maliyet Yükle (PDF / Excel) | PetroTek",
    on_load=QuoteState.set_active_module("Maliyet Yükle (PDF / Excel)"),
)


# Akıllı Tedarikçi Karşılaştırma Sayfası
app.add_page(
    supplier_compare_page,
    route="/tedarikci-karsilastir",
    title="Akıllı Tedarikçi Karşılaştırma & Sepet Optimizasyonu | PetroTek",
    on_load=[
        QuoteState.set_active_module("Akıllı Tedarikçi Karşılaştırma & Sepet O..."),
        SupplierCompareState.teklifleri_guncelle,  # <-- Veritabanından teklifleri yükler
    ],
)