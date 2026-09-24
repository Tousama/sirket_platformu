import reflex as rx
from .engineer_state import EngineerState
from .quote_builder import sidebar


def engineer_main() -> rx.Component:
  return rx.box(
      rx.vstack(
          # 1. Üst Navigasyon Barı
          rx.hstack(
              rx.hstack(
                  rx.icon("menu", size=18, color="#94a3b8", cursor="pointer"),
                  rx.icon("users", size=16, color="#cbd5e1"),
                  rx.heading(
                      "Mühendis Yönetimi",
                      size="4",
                      color="#ffffff",
                      font_weight="700",
                  ),
                  rx.text("/", color="#475569"),
                  rx.text(
                      "PetroTek Engineering", color="#94a3b8", font_size="13px"
                  ),
                  spacing="2",
                  align_items="center",
              ),
              rx.spacer(),
              rx.hstack(
                  rx.segmented_control.root(
                      rx.segmented_control.item("TRY (₺)", value="TRY (₺)"),
                      rx.segmented_control.item("USD ($)", value="USD ($)"),
                      rx.segmented_control.item("EUR (€)", value="EUR (€)"),
                      value=EngineerState.currency,
                      on_change=EngineerState.set_currency,
                      radius="full",
                      size="1",
                  ),
                  rx.button(
                      rx.icon("plus", size=15),
                      "Yeni Teklif",
                      color_scheme="blue",
                      size="2",
                      radius="full",
                      on_click=rx.redirect("/teklif-hazirla"),
                  ),
                  rx.icon_button(
                      rx.icon("bell", size=16),
                      variant="ghost",
                      color_scheme="gray",
                      size="2",
                  ),
                  spacing="3",
                  align_items="center",
              ),
              width="100%",
              padding_bottom="16px",
              border_bottom="1px solid #151e33",
          ),
          # 2. Modül Başlığı ve İkon
          rx.vstack(
              rx.hstack(
                  rx.icon("users", size=18, color="#38bdf8"),
                  rx.heading(
                      "Mühendis Ekibi Yönetimi",
                      size="4",
                      color="#ffffff",
                      font_weight="700",
                  ),
                  spacing="2",
                  align_items="center",
              ),
              rx.text(
                  "Tekliflerde sorumlu mühendis olarak atanacak ekip"
                  " üyelerini ve unvanlarını yönetin.",
                  font_size="12.5px",
                  color="#94a3b8",
              ),
              spacing="1",
              align_items="start",
              padding_top="6px",
              padding_bottom="8px",
          ),
          # 3. İki Kolonlu Düzen: Sol (Ekleme Formu) - Sağ (Aktif Mühendisler Tablosu)
          rx.grid(
              # SOL KART: Yeni Mühendis Ekle
              rx.box(
                  rx.vstack(
                      rx.text(
                          "YENİ MÜHENDİS EKLE",
                          font_size="12px",
                          font_weight="800",
                          color="#38bdf8",
                          letter_spacing="0.02em",
                      ),
                      rx.vstack(
                          rx.text(
                              "Ad Soyad:", font_size="11.5px", color="#94a3b8"
                          ),
                          rx.input(
                              placeholder="Örn: Ahmet Yılmaz",
                              value=EngineerState.yeni_ad_soyad,
                              on_change=EngineerState.set_yeni_ad_soyad,
                              size="2",
                              width="100%",
                              background="#040813",
                              border="1px solid #1e293b",
                          ),
                          width="100%",
                          spacing="1",
                          align_items="start",
                      ),
                      rx.vstack(
                          rx.text(
                              "Unvan:", font_size="11.5px", color="#94a3b8"
                          ),
                          rx.input(
                              placeholder="Elektrik-Elektronik Mühendisi",
                              value=EngineerState.yeni_unvan,
                              on_change=EngineerState.set_yeni_unvan,
                              size="2",
                              width="100%",
                              background="#040813",
                              border="1px solid #1e293b",
                          ),
                          width="100%",
                          spacing="1",
                          align_items="start",
                      ),
                      rx.button(
                          "Ekibe Ekle",
                          background="#0284c7",
                          _hover={"background": "#0369a1"},
                          color="#ffffff",
                          size="2",
                          font_weight="700",
                          border_radius="6px",
                          width="100%",
                          cursor="pointer",
                          on_click=EngineerState.add_engineer,
                          margin_top="6px",
                      ),
                      spacing="3",
                      width="100%",
                  ),
                  background="#080e1a",
                  border="1px solid #1a2538",
                  border_radius="10px",
                  padding="20px 24px",
                  width="100%",
                  height="fit-content",
              ),
              # SAĞ KART: Aktif Mühendisler Tablosu (Silme Butonlu)
              rx.box(
                  rx.vstack(
                      rx.text(
                          "Aktif Mühendisler",
                          font_size="13px",
                          font_weight="700",
                          color="#ffffff",
                          padding_bottom="4px",
                      ),
                      rx.table.root(
                          rx.table.header(
                              rx.table.row(
                                  rx.table.column_header_cell(
                                      "ID", font_size="11px", color="#64748b"
                                  ),
                                  rx.table.column_header_cell(
                                      "ADI SOYADI",
                                      font_size="11px",
                                      color="#64748b",
                                  ),
                                  rx.table.column_header_cell(
                                      "UNVAN",
                                      font_size="11px",
                                      color="#64748b",
                                  ),
                                  rx.table.column_header_cell(
                                      "İŞLEM",
                                      font_size="11px",
                                      color="#64748b",
                                      text_align="center",
                                  ),
                              )
                          ),
                          rx.table.body(
                              rx.foreach(
                                  EngineerState.engineers,
                                  lambda eng: rx.table.row(
                                      rx.table.cell(
                                          rx.text(
                                              eng["id"].to(str),
                                              font_size="12px",
                                              color="#94a3b8",
                                          )
                                      ),
                                      rx.table.cell(
                                          rx.text(
                                              eng["ad_soyad"].to(str),
                                              font_size="12.5px",
                                              font_weight="bold",
                                              color="#ffffff",
                                          )
                                      ),
                                      rx.table.cell(
                                          rx.text(
                                              eng["unvan"].to(str),
                                              font_size="12px",
                                              color="#cbd5e1",
                                          )
                                      ),
                                      # Silme Butonu
                                      rx.table.cell(
                                          rx.icon_button(
                                              rx.icon("trash-2", size=14),
                                              variant="ghost",
                                              color_scheme="ruby",
                                              size="1",
                                              cursor="pointer",
                                              on_click=EngineerState.remove_engineer(
                                                  eng["id"].to(int),
                                                  eng["ad_soyad"].to(str),
                                              ),
                                          ),
                                          text_align="center",
                                      ),
                                      align="center",
                                  ),
                              )
                          ),
                          width="100%",
                      ),
                      width="100%",
                      spacing="2",
                  ),
                  background="#080e1a",
                  border="1px solid #1a2538",
                  border_radius="10px",
                  padding="20px 24px",
                  width="100%",
              ),
              columns="2",
              spacing="4",
              width="100%",
          ),
          spacing="4",
          width="100%",
      ),
      padding="20px 32px",
      flex="1",
      overflow_y="auto",
      height="100vh",
      background="#030712",
  )


def engineer_page() -> rx.Component:
  return rx.hstack(
      sidebar(),
      engineer_main(),
      spacing="0",
      width="100%",
      height="100vh",
      overflow="hidden",
      on_mount=EngineerState.on_load,
  )