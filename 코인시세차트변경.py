import sys
import requests
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QSplitter,
    QGroupBox
)
from PySide6.QtCore import Qt
import pyqtgraph as pg

class CoinPriceUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("코인 시세 / 검색 / 차트 (차트 스타일 적용)")
        self.resize(1000, 600)

        # ======== 검색 영역 그룹박스 ========
        self.searchLine = QLineEdit()
        self.searchLine.setPlaceholderText("코인 이름 또는 키워드를 입력하세요 (예: bit)")
        self.searchBtn = QPushButton("검색")
        self.top10Btn = QPushButton("Top 10 불러오기")

        groupBox = QGroupBox("검색 및 설정")
        groupLayout = QHBoxLayout()
        groupLayout.addWidget(self.searchLine)
        groupLayout.addWidget(self.searchBtn)
        groupLayout.addWidget(self.top10Btn)
        groupBox.setLayout(groupLayout)

        # ======== 테이블 (코인 목록 표시) ========
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["코인", "가격(USD)", "변동률(24h)"])
        self.table.cellClicked.connect(self.on_table_cell_clicked)

        # ======== 차트 (PyQtGraph) ========
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.setTitle("가격 변동 차트")
        
        # -- 차트 배경/그리드/축 스타일 변경 --
        self.plotWidget.setBackground('#2b2b2b')  # 다크 배경 (원하는 색상으로 변경 가능)
        plotItem = self.plotWidget.getPlotItem()
        plotItem.showGrid(x=True, y=True, alpha=0.3)  # 그리드 표시, alpha=투명도
        # 축 라벨 색상
        plotItem.getAxis('left').setTextPen('#eeeeee')
        plotItem.getAxis('bottom').setTextPen('#eeeeee')

        # 메인 Splitter (테이블 + 차트)
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)

        tableContainer = QWidget()
        tableLayout = QVBoxLayout()
        tableLayout.addWidget(self.table)
        tableContainer.setLayout(tableLayout)

        chartContainer = QWidget()
        chartLayout = QVBoxLayout()
        chartLayout.addWidget(self.plotWidget)
        chartContainer.setLayout(chartLayout)

        splitter.addWidget(tableContainer)
        splitter.addWidget(chartContainer)
        splitter.setSizes([400, 600])

        # 메인 레이아웃
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(groupBox)
        mainLayout.addWidget(splitter)

        container = QWidget()
        container.setLayout(mainLayout)
        self.setCentralWidget(container)

        # ======== 시그널 연결 ========
        self.searchBtn.clicked.connect(self.search_coins)
        self.top10Btn.clicked.connect(self.load_top10)

        self.coin_ids = []
        self.load_top10()  # 초기 Top 10 로드

    def load_top10(self):
        """시가총액 상위 10개 코인 정보를 불러와 테이블에 표시"""
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 10,
            "page": 1,
            "sparkline": "false"
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                print(f"API 호출 실패: {response.status_code}")
                return
            data = response.json()
            if not isinstance(data, list):
                print("API 응답이 리스트 형태가 아닙니다:", data)
                return
        except Exception as e:
            print("Top 10 불러오기 실패:", e)
            return

        self.update_table(data)

    def update_table(self, data):
        """공통적으로 테이블 갱신하는 함수"""
        self.table.setRowCount(len(data))
        self.coin_ids = []

        for row, coin in enumerate(data):
            if not isinstance(coin, dict):
                continue

            name = coin.get("name", "N/A")
            current_price = coin.get("current_price", "N/A")
            change_24h = coin.get("price_change_percentage_24h", "N/A")

            self.table.setItem(row, 0, QTableWidgetItem(str(name)))
            self.table.setItem(row, 1, QTableWidgetItem(str(current_price)))
            if isinstance(change_24h, (int, float)):
                self.table.setItem(row, 2, QTableWidgetItem(f"{change_24h:.2f}%"))
            else:
                self.table.setItem(row, 2, QTableWidgetItem(str(change_24h)))

            coin_id = coin.get("id", "")
            self.coin_ids.append(coin_id)

    def search_coins(self):
        """검색어를 바탕으로 CoinGecko 검색 API 호출 후 결과를 테이블에 표시"""
        query = self.searchLine.text().strip()
        if not query:
            return

        url = "https://api.coingecko.com/api/v3/search"
        params = {"query": query}
        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                print(f"검색 API 호출 실패: {response.status_code}")
                return
            data = response.json()
            coins_data = data.get("coins", [])
        except Exception as e:
            print("검색 실패:", e)
            return

        detailed_data = []
        for coin in coins_data[:10]:
            coin_id = coin.get("id", "")
            if not coin_id:
                continue
            market_url = "https://api.coingecko.com/api/v3/coins/markets"
            market_params = {
                "vs_currency": "usd",
                "ids": coin_id
            }
            try:
                market_response = requests.get(market_url, params=market_params)
                if market_response.status_code == 200:
                    market_info = market_response.json()
                    if market_info and isinstance(market_info, list):
                        detailed_data.append(market_info[0])
            except Exception as e:
                print(f"코인 시세 가져오기 실패 ({coin_id}):", e)

        self.update_table(detailed_data)

    def on_table_cell_clicked(self, row, column):
        """테이블 행 클릭 시 해당 코인의 차트 표시"""
        if row < 0 or row >= len(self.coin_ids):
            return
        coin_id = self.coin_ids[row]
        if coin_id:
            self.update_chart(coin_id)

    def update_chart(self, coin_id):
        """해당 코인의 7일(일주일) 차트 데이터 불러와서 표시"""
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "7",
            "interval": "daily"
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                print(f"차트 API 호출 실패: {response.status_code}")
                return
            data = response.json()
            prices = data.get("prices", [])
        except Exception as e:
            print("차트 데이터 불러오기 실패:", e)
            return

        if not prices:
            print("차트 데이터가 없습니다.")
            return

        x = list(range(len(prices)))
        y = [p[1] for p in prices]

        # 차트 그리기 (선 두께, 색상, 심볼 스타일 등 지정)
        self.plotWidget.clear()
        
        # 예: 초록색 선, 두께=2 / 심볼=원, 심볼 크기=6, 심볼 내부 흰색, 테두리 초록
        pen = pg.mkPen(color='lime', width=2)
        symbolBrush = pg.mkBrush('white')
        symbolPen = pg.mkPen('lime')
        
        self.plotWidget.plot(
            x, y,
            pen=pen,
            symbol='o',
            symbolSize=6,
            symbolBrush=symbolBrush,
            symbolPen=symbolPen
        )
        self.plotWidget.setTitle(f"{coin_id} - 7일 가격 변동 (USD)")

def main():
    app = QApplication(sys.argv)
    window = CoinPriceUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
