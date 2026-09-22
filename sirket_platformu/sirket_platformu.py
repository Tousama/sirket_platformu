import reflex as rx
from .dashboard_view import dashboard_page
from .quote_builder import quote_builder_page
from .quote_state import QuoteState
from .dashboard_state import DashboardState
from .technical_scope_view import technical_scope_page



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