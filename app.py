import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Polygon
import math
import matplotlib_fontja


# ページ設定
st.set_page_config(
    page_title="トラック入るくん",
    page_icon="🚛",
    layout="wide"
)

# カスタムCSS
st.markdown("""
<style>
    .big-font {
        font-size: 28px !important;
        font-weight: bold;
        color: #1E88E5;
    }
    .result-box {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        padding: 25px;
        border-radius: 15px;
        margin: 15px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .spacer-value {
        font-size: 56px;
        font-weight: bold;
        color: #E91E63;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .success-box {
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
    }
    .warning-box {
        background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FF9800;
    }
    .error-box {
        background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #F44336;
    }
</style>
""", unsafe_allow_html=True)

# タイトル
st.title("🚛 トラック入るくん")
st.subheader("トラックに製品が入るかどうか計算します")

# サイドバー：入力フォーム
st.sidebar.header("📐 入力パラメータ")

st.sidebar.subheader("🚛 トラック情報")
truck_bed_length = st.sidebar.number_input(
    "荷台長さ (mm)",
    min_value=1000,
    max_value=20000,
    value=10000,
    step=100
)

truck_bed_height = st.sidebar.number_input(
    "荷台床高さ (mm)",
    min_value=100,
    max_value=3000,
    value=1100,
    step=50,
    help="地面から荷台床面までの高さ"
)

roof_carrier_height = st.sidebar.number_input(
    "ルーフキャリア高さ (mm)",
    min_value=1000,
    max_value=5000,
    value=2700,
    step=50,
    help="地面からルーフキャリア上端までの高さ"
)

st.sidebar.subheader("🔵 製品情報")
L_prod = st.sidebar.number_input(
    "製品長さ (mm)",
    min_value=1000,
    max_value=30000,
    value=12000,
    step=1
)

prod_width = st.sidebar.number_input(
    "製品幅（太さ）(mm)",
    min_value=10,
    max_value=1000,
    value=250,
    step=1
)

st.sidebar.subheader("📦 積載制限（許容範囲）")
W_max = st.sidebar.number_input(
    "許容横幅 (mm)",
    min_value=1000,
    max_value=30000,
    value=10000,
    step=100
)

H_max = st.sidebar.number_input(
    "許容高さ (mm)",
    min_value=1000,
    max_value=8000,
    value=3000,
    step=50
)

st.sidebar.subheader("🔴 スペーサー設定")
X_spacer = st.sidebar.number_input(
    "荷台後端からの距離 (mm)",
    min_value=0,
    max_value=5000,
    value=10,
    step=1
)

spacer_height_input = st.sidebar.number_input(
    "スペーサー高さ (mm)",
    min_value=0,
    max_value=5000,
    value=600,
    step=1,
    help="スペーサーの高さ（荷台床面から）"
)

# スペーサー幅は描画用に固定値
spacer_width_mm = 50

# 計算ロジック
def calculate_with_spacer_height(L_prod, prod_width, W_max, H_max, X_spacer, spacer_height,
                                  truck_bed_length, truck_bed_height, roof_carrier_height):
    """
    指定されたスペーサー高さで、許容範囲に収まるかを計算
    
    構成:
    - スペーサー: 製品の左下を支える（荷台後端側）
    - ルーフキャリア: 製品が通過する点（キャビン側）
    - 製品: スペーサー → ルーフキャリア → 右上へ伸びる
    """
    results = {
        'error': None,
        'warning': None,
        'success': None,
        'angle_rad': 0,
        'angle_deg': 0,
        'spacer_height_mm': spacer_height,
        'product_top_height': 0,
        'product_right_x': 0,
        'can_fit': True
    }
    
    # 基本パラメータ
    roof_x = truck_bed_length  # ルーフキャリアのX位置
    roof_y = roof_carrier_height  # ルーフキャリアの高さ（地面から）
    half_width = prod_width / 2
    dist_to_roof = roof_x - X_spacer  # スペーサーからルーフキャリアまでの水平距離
    
    if dist_to_roof <= 0:
        results['error'] = "スペーサー位置がルーフキャリアより右にあります"
        results['can_fit'] = False
        return results
    
    # スペーサー上端の高さ（地面から）
    spacer_top = truck_bed_height + spacer_height
    
    # スペーサーからルーフキャリアへの角度を計算
    # tan(θ) = (roof_y - spacer_top) / dist_to_roof
    dy = roof_y - spacer_top
    
    if dy < 0:
        results['warning'] = "スペーサーがルーフキャリアより高いです"
        # 製品は下向きになる可能性があるが、計算は続行
    
    tan_theta = dy / dist_to_roof
    theta_rad = math.atan(tan_theta)
    theta_deg = math.degrees(theta_rad)
    sin_theta = math.sin(theta_rad)
    cos_theta = math.cos(theta_rad)
    
    # 製品先端位置を計算
    # 製品下面先端のY座標
    product_bottom_tip_y = spacer_top + L_prod * sin_theta
    # 製品上面先端のY座標（製品幅全体を足す）
    product_top_height = product_bottom_tip_y + prod_width * abs(cos_theta)
    # 製品右端X（製品幅を考慮）
    product_right_x = X_spacer + L_prod * cos_theta + prod_width * abs(sin_theta)
    
    results['angle_rad'] = theta_rad
    results['angle_deg'] = theta_deg
    results['product_top_height'] = product_top_height
    results['product_right_x'] = product_right_x
    
    # 許容範囲チェック
    width_ok = product_right_x <= W_max + 1  # 1mm誤差許容
    height_ok = product_top_height <= H_max + 1
    
    if not width_ok and not height_ok:
        results['error'] = f"許容横幅({product_right_x:.0f}mm > {W_max}mm)と許容高さ({product_top_height:.0f}mm > {H_max}mm)を超えています"
        results['can_fit'] = False
    elif not width_ok:
        results['error'] = f"許容横幅 {W_max}mm を超えます（{product_right_x:.0f}mm）。"
        results['can_fit'] = False
    elif not height_ok:
        results['error'] = f"許容高さ {H_max}mm を超えます（{product_top_height:.0f}mm）。"
        results['can_fit'] = False
    else:
        results['success'] = f"✅ 許容範囲内（横: {product_right_x:.0f}mm, 高さ: {product_top_height:.0f}mm）"
    
    return results

# 計算実行
results = calculate_with_spacer_height(L_prod, prod_width, W_max, H_max, X_spacer, spacer_height_input,
                                        truck_bed_length, truck_bed_height, roof_carrier_height)

# メインパネル - 計算結果を上部に
st.header("📊 計算結果")

result_col1, result_col2, result_col3 = st.columns([2, 1, 1])

with result_col1:
    if results['error']:
        st.markdown(f"""
        <div class="error-box">
            ❌ <strong>エラー</strong><br>
            {results['error']}
        </div>
        """, unsafe_allow_html=True)
    elif results['warning']:
        st.markdown(f"""
        <div class="warning-box">
            ⚠️ <strong>注意</strong><br>
            {results['warning']}
        </div>
        """, unsafe_allow_html=True)
    
    if results['spacer_height_mm'] > 0:
        st.markdown(f"""
        <div class="result-box">
            <p class="big-font">🎯 必要なスペーサー高さ</p>
            <p class="spacer-value">{results['spacer_height_mm']:.0f} mm</p>
        </div>
        """, unsafe_allow_html=True)
        
        if results['success']:
            st.markdown(f"""
            <div class="success-box">
                {results['success']}
            </div>
            """, unsafe_allow_html=True)
    elif results['can_fit']:
        st.markdown(f"""
        <div class="result-box">
            <p class="big-font">🎯 スペーサー不要</p>
            <p style="font-size: 24px; color: #4CAF50;">スペーサーなしで許容範囲に収まります</p>
        </div>
        """, unsafe_allow_html=True)

with result_col2:
    st.metric("積載角度", f"{results['angle_deg']:.1f}°")
    st.metric("製品右端X", f"{results['product_right_x']:.0f} mm")

with result_col3:
    st.metric("製品最高点", f"{results['product_top_height']:.0f} mm")
    st.metric("製品長さ", f"{L_prod} mm")

st.markdown("---")

# トラック積載イメージ図を大きく表示
st.header("📐 トラック積載イメージ図")

fig, ax = plt.subplots(1, 1, figsize=(18, 9))
fig.patch.set_facecolor('#F5F5F5')
ax.set_facecolor('#87CEEB')

scale = 0.001

# 地面
ground = patches.Rectangle((-2, -0.3), 20, 0.3,
                            facecolor='#8D6E63', edgecolor='#5D4037', linewidth=2)
ax.add_patch(ground)

bed_h = truck_bed_height * scale
bed_len = truck_bed_length * scale
roof_h = roof_carrier_height * scale

# キャビン
cabin_x = bed_len + 0.1
cabin_height = roof_h - bed_h + 0.5
cabin = FancyBboxPatch(
    (cabin_x, bed_h - 0.3), 1.5, cabin_height,
    boxstyle="round,pad=0.02,rounding_size=0.1",
    facecolor='#FFFFFF', edgecolor='#333333', linewidth=2
)
ax.add_patch(cabin)

window = patches.Rectangle(
    (cabin_x + 0.15, bed_h + 0.6), 1.2, 0.7,
    facecolor='#B3E5FC', edgecolor='#333333', linewidth=1.5
)
ax.add_patch(window)

# ルーフキャリア
roof_carrier = patches.Rectangle(
    (bed_len - 0.1, roof_h - 0.05), 1.7, 0.1,
    facecolor='#455A64', edgecolor='#263238', linewidth=2
)
ax.add_patch(roof_carrier)

# タイヤ
for wx in [1.2, 2.5, cabin_x + 0.8]:
    wheel = Circle((wx, 0.4), 0.4, facecolor='#333333', edgecolor='#1A1A1A', linewidth=2)
    ax.add_patch(wheel)
    hub = Circle((wx, 0.4), 0.15, facecolor='#666666')
    ax.add_patch(hub)

# 荷台
frame = patches.Rectangle((0, bed_h - 0.15), bed_len, 0.15,
                            facecolor='#607D8B', edgecolor='#455A64', linewidth=2)
ax.add_patch(frame)

bed_floor = patches.Rectangle((0, bed_h), bed_len, 0.05,
                                facecolor='#795548', edgecolor='#5D4037', linewidth=1)
ax.add_patch(bed_floor)

# スペーサー
spacer_x_pos = X_spacer * scale
spacer_h = results['spacer_height_mm'] * scale
sw = spacer_width_mm * scale

if results['spacer_height_mm'] > 0:
    spacer_draw_x = spacer_x_pos - sw / 2
    spacer_draw_y = bed_h + 0.05
    
    spacer_rect = FancyBboxPatch(
        (spacer_draw_x, spacer_draw_y), sw, spacer_h,
        boxstyle="round,pad=0.01,rounding_size=0.02",
        facecolor='#E91E63', edgecolor='#880E4F', 
        linewidth=3, alpha=0.95, zorder=15
    )
    ax.add_patch(spacer_rect)
    
    # 寸法線
    dim_x = spacer_draw_x - 0.15
    ax.annotate('', xy=(dim_x, spacer_draw_y + spacer_h),
               xytext=(dim_x, spacer_draw_y),
               arrowprops=dict(arrowstyle='<->', color='#E91E63', lw=3))
    
    ax.text(dim_x - 0.1, spacer_draw_y + spacer_h / 2,
           f'{results["spacer_height_mm"]:.0f}mm\n({results["spacer_height_mm"]/10:.1f}cm)',
           fontsize=14, color='#E91E63', fontweight='bold', 
           va='center', ha='right',
           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                    edgecolor='#E91E63', linewidth=2, alpha=0.95))

# 製品描画
L_prod_m = L_prod * scale
prod_w = prod_width * scale
half_w = prod_w / 2

# スペーサー上端 = 製品の下面左端が接する点
spacer_top_x = spacer_x_pos
spacer_top_y = bed_h + 0.05 + spacer_h

roof_touch_x = bed_len
roof_touch_y = roof_h

# 製品の傾きを計算（製品下面がスペーサー上端→ルーフキャリアを結ぶ）
dx = roof_touch_x - spacer_top_x
dy = roof_touch_y - spacer_top_y
theta = math.atan2(dy, dx) if dx > 0 else 0

cos_t = math.cos(theta)
sin_t = math.sin(theta)

# 製品下面の左端と右端（スペーサー上端とルーフキャリアを結ぶ線）
left_bottom = (spacer_top_x, spacer_top_y)
right_bottom = (spacer_top_x + L_prod_m * cos_t, spacer_top_y + L_prod_m * sin_t)

# 製品幅（厚み）の方向 = 傾きに垂直な上方向
normal_x = -sin_t * prod_w
normal_y = cos_t * prod_w

# 4つの角：下面左端、下面右端、上面右端、上面左端
corners = [
    left_bottom,
    right_bottom,
    (right_bottom[0] + normal_x, right_bottom[1] + normal_y),
    (left_bottom[0] + normal_x, left_bottom[1] + normal_y),
]

prod_color = '#F44336' if results['error'] else '#1565C0'

product_shape = Polygon(corners, closed=True, 
                        facecolor=prod_color, 
                        edgecolor='#0D47A1' if not results['error'] else '#B71C1C',
                        linewidth=2, alpha=0.9, zorder=10)
ax.add_patch(product_shape)

# 接触点をマーク
ax.plot(spacer_top_x, spacer_top_y, 'o', color='#E91E63', markersize=10, zorder=25)
ax.plot(roof_touch_x, roof_touch_y, 'o', color='#FF5722', markersize=12, zorder=25)
ax.text(roof_touch_x + 0.15, roof_touch_y + 0.1, 'ルーフキャリア', fontsize=10, color='#FF5722', fontweight='bold')

# 製品ラベル
mid_x = spacer_top_x + L_prod_m * cos_t / 2 + normal_x / 2
mid_y = spacer_top_y + L_prod_m * sin_t / 2 + normal_y / 2
ax.text(mid_x, mid_y + 0.3, f'製品 {L_prod}mm',
        fontsize=12, fontweight='bold', color=prod_color,
        ha='center', va='bottom',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=prod_color, alpha=0.9))

# 許容高さ（点線）
ax.axhline(y=H_max * scale, color='#F44336', linestyle='--', linewidth=2, alpha=0.8)
ax.text(0.3, H_max * scale + 0.05, f'許容高さ {H_max}mm', fontsize=10, color='#F44336', fontweight='bold')

# 許容横幅（縦点線）
ax.axvline(x=W_max * scale, color='#FF9800', linestyle='--', linewidth=2, alpha=0.8)
ax.text(W_max * scale + 0.05, bed_h + 0.5, f'許容横幅 {W_max}mm', fontsize=10, color='#FF9800', fontweight='bold', rotation=90)

# グラフ設定
ax.set_xlim(-1.5, max(bed_len + 3, W_max * scale + 0.5))
ax.set_ylim(-0.5, max(H_max * scale + 0.5, results['product_top_height'] * scale + 0.3))
ax.set_aspect('equal')
ax.set_xlabel('横方向 (m)', fontsize=12, fontweight='bold')
ax.set_ylabel('高さ (m)', fontsize=12, fontweight='bold')
ax.set_title('トラック積載イメージ図', fontsize=18, fontweight='bold', pad=20)
ax.grid(True, alpha=0.3, linestyle='--')


plt.tight_layout()
st.pyplot(fig)
plt.close()

# フッター
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #9E9E9E;">
    LoadMaster Spacer v3.3 | スペーサー高さ調整対応
</div>
""", unsafe_allow_html=True)
