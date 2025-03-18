import sys
import requests
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QSplitter,
    QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
import pyqtgraph as pg

class CoinPriceUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("코인 시세 / 검색 / 차트")
        self.resize(1000, 600)

        # ======== 위젯 정의 ========
        # 상단 검색 레이아웃
        self.searchLine = QLineEdit()
        self.searchLine.setPlaceholderText("코인 이름 또는 키워드를 입력하세요 (예: bit)")
        self.searchBtn = QPushButton("검색")
        self.top10Btn = QPushButton("Top 10 불러오기")

        # 테이블 (코인 목록 표시)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["코인", "가격(USD)", "변동률(24h)"])
        self.table.cellClicked.connect(self.on_table_cell_clicked)

        # 차트 (PyQtGraph)
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.setTitle("가격 변동 차트")
        self.plotWidget.setLabel('left', '가격 (USD)')
        self.plotWidget.setLabel('bottom', '일일 단위 (임의)')

        # 레이아웃/컨테이너
        topLayout = QHBoxLayout()
        topLayout.addWidget(self.searchLine)
        topLayout.addWidget(self.searchBtn)
        topLayout.addWidget(self.top10Btn)

        # Splitter로 테이블과 차트를 나눔
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)

        # 테이블을 담을 컨테이너
        tableContainer = QWidget()
        tableLayout = QVBoxLayout()
        tableLayout.addWidget(self.table)
        tableContainer.setLayout(tableLayout)

        # 차트를 담을 컨테이너
        chartContainer = QWidget()
        chartLayout = QVBoxLayout()
        chartLayout.addWidget(self.plotWidget)
        chartContainer.setLayout(chartLayout)

        splitter.addWidget(tableContainer)
        splitter.addWidget(chartContainer)
        splitter.setSizes([400, 600])  # 초기 크기 비율

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(topLayout)
        mainLayout.addWidget(splitter)

        container = QWidget()
        container.setLayout(mainLayout)
        self.setCentralWidget(container)

        # ======== 시그널 연결 ========
        self.searchBtn.clicked.connect(self.search_coins)
        self.top10Btn.clicked.connect(self.load_top10)

        # 코인 ID 목록 저장 (테이블 클릭 시 차트에 활용)
        self.coin_ids = []

        # 초기 상태로 Top 10 로드
        self.load_top10()

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
            # data가 리스트인지 확인
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
            # coin이 딕셔너리 형태인지 확인
            if not isinstance(coin, dict):
                continue

            name = coin.get("name", "N/A")
            current_price = coin.get("current_price", "N/A")
            change_24h = coin.get("price_change_percentage_24h", "N/A")

            # 테이블에 값 세팅
            self.table.setItem(row, 0, QTableWidgetItem(str(name)))
            self.table.setItem(row, 1, QTableWidgetItem(str(current_price)))
            # 변동률이 숫자라면 소수점 2자리로 표시
            if isinstance(change_24h, (int, float)):
                self.table.setItem(row, 2, QTableWidgetItem(f"{change_24h:.2f}%"))
            else:
                self.table.setItem(row, 2, QTableWidgetItem(str(change_24h)))

            # 차트 조회용 ID 저장
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

        # 검색 결과에 있는 코인들의 시세(가격/변동률)를 가져오기 위해
        # /coins/markets 엔드포인트를 다시 호출해야 합니다.
        # 예시로, 검색 결과 중 최대 10개만 상세 정보를 불러와 테이블에 표시해볼게요.
        detailed_data = []
        for coin in coins_data[:10]:
            coin_id = coin.get("id", "")
            if not coin_id:
                continue
            # 코인 상세 시세 불러오기
            market_url = "https://api.coingecko.com/api/v3/coins/markets"
            market_params = {
                "vs_currency": "usd",
                "ids": coin_id
            }
            try:
                market_response = requests.get(market_url, params=market_params)
                if market_response.status_code == 200:
                    market_info = market_response.json()
                    # market_info가 리스트 형태일 것이므로 첫 번째 항목만 가져옴
                    if market_info and isinstance(market_info, list):
                        detailed_data.append(market_info[0])
            except Exception as e:
                print(f"코인 시세 가져오기 실패 ({coin_id}):", e)

        # 이제 detailed_data를 테이블에 표시
        self.update_table(detailed_data)

    def on_table_cell_clicked(self, row, column):
        """테이블 행 클릭 시 해당 코인의 차트 표시"""
        if row < 0 or row >= len(self.coin_ids):
            return
        coin_id = self.coin_ids[row]
        if coin_id:
            self.update_chart(coin_id)

    def update_chart(self, coin_id):
        """해당 코인의 1일(24시간) 차트 데이터 불러와서 표시"""
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "7",       # 1일
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

        # 시간축(인덱스)와 가격 리스트
        x = list(range(len(prices)))
        y = [p[1] for p in prices]  # p = [timestamp, price]

        # 차트 그리기
        self.plotWidget.clear()
        self.plotWidget.plot(x, y, pen='b', symbol='o', symbolSize=5)
        self.plotWidget.setTitle(f"{coin_id} - 1일 가격 변동")

def main():
    app = QApplication(sys.argv)
    window = CoinPriceUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
