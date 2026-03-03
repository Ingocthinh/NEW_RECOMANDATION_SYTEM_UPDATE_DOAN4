<img width="1907" height="1035" alt="image" src="https://github.com/user-attachments/assets/acb90375-c70f-4d20-9508-306fa0fef526" />\
#link dự án dowload:https://drive.google.com/file/d/1iP55iU8hGVNd--ODe9cin-Xg8f9ezlzu/view?usp=drive_link

# Hệ Thống Gợi Ý Tin Tức Cá Nhân Hóa (Thesis Level)

Dự án này là một nền tảng gợi ý tin tức toàn diện, ứng dụng kỹ thuật học máy (Machine Learning) để cung cấp trải nghiệm đọc tin tối ưu cho người dùng. Hệ thống tự động thu thập tin tức, phân tích nội dung và hành vi người dùng để đưa ra các gợi ý chính xác và có chiều sâu.

## 🌟 Tính Năng Nổi Bật

-   **Thu thập tin tức tự động (Crawler)**: Tự động quét và bóc tách nội dung từ VnExpress (9 chủ đề: Công nghệ, Kinh tế, Thể thao, Sức khỏe, Giải trí, Giáo dục, Du lịch, Pháp luật, Thời sự).
-   **Gợi ý Hybrid (Hybrid Recommendation)**: Kết hợp Content-Based Filtering (Dựa trên nội dung) và Collaborative Filtering (Lọc cộng tác - SVD) cùng với hồ sơ người dùng (Category Preference).
-   **Theo dõi hành vi người dùng (Real-time Tracking)**: Tự động ghi lại các tương tác như Click, View, Dwell Time (thời gian đọc) để cập nhật mô hình gợi ý ngay lập tức.
-   **Giao diện Dashboard hiện đại**: Thiết kế Premium với chế độ Sáng/Tối (Light/Dark mode), Skeleton Loading và hiệu ứng mượt mà.
-   **Sắp xếp theo độ liên quan (Score Sorting)**: Luôn hiển thị các bài báo có điểm số gợi ý cao nhất lên đầu.
-   **Lọc đa dạng (Diversity Penalty)**: Tránh việc gợi ý quá nhiều tin từ một chủ đề, đảm bảo nguồn tin phong phú.

## 🚀 Công Nghệ Sử Dụng

### Frontend
-   **React + TypeScript + Vite**: Đảm bảo tốc độ và độ ổn định cao.
-   **Framer Motion**: Xử lý các hiệu ứng chuyển động chuyên nghiệp.
-   **Vanilla CSS**: Tối ưu hóa hiệu năng và tính linh hoạt trong thiết kế.

### Backend
-   **Node.js (Express)**: Xây dựng RESTful API mạnh mẽ.
-   **Prisma ORM**: Quản lý cơ sở dữ liệu một cách an toàn và dễ dàng.
-   **SQLite**: Lưu trữ dữ liệu gọn nhẹ nhưng hiệu quả cho môi trường phát triển.

### Machine Learning Service
-   **Python (Flask)**: Dịch vụ API dành riêng cho tính toán logic gợi ý.
-   **Scikit-learn & SciPy**: Xử lý vector hóa văn bản (TF-IDF) và phân tích ma trận (SVD).
-   **Vietnamese NLP**: Tối ưu hóa bóc tách văn bản tiếng Việt với hỗ trợ Trigrams.

## 🛠️ Hướng Dẫn Cài Đặt & Chạy

### 1. Yêu cầu hệ thống
-   Python 3.10+
-   Node.js 18+
-   NPM

### 2. Cấu hình dịch vụ ML
```bash
cd ml_service
pip install -r requirements.txt
python app.py
```

### 3. Cấu hình Backend
```bash
cd backend
npm install
npx prisma db push
npm run dev
```

### 4. Cấu hình Frontend
```bash
cd frontend
npm install
npm run dev
```

*Lưu ý: Nếu bạn gặp lỗi Execution Policy trên Windows, hãy sử dụng `npm.cmd` thay vì `npm`.*

## 📊 Kiến Trúc Dữ Liệu

Hệ thống sử dụng mô hình Hybrid phân cấp:
1.  **Content Weight (0.35)**: Dựa trên sự tương đồng về nội dung bài báo người dùng đã đọc.
2.  **Collaborative Weight (0.45)**: Dự báo dựa trên sở thích của những người dùng tương đồng.
3.  **Category Weight (0.20)**: Điều chỉnh dựa trên sở thích chủ đề (Ví dụ: Người dùng hay đọc tin "Công nghệ").

## 🛡️ Tài Khoản Kiểm Thử (Demo)
Bạn có thể sử dụng tài khoản sau để đăng nhập vào trang quản lý:
-   **Email**: `demo@example.com`
-   **Mật khẩu**: `password123`

## � Cấu Trúc Dự Án
```
newrecomandationsystem/
├── frontend/       # Ứng dụng React (Giao diện)
├── backend/        # API Node.js & Database Schema
├── ml_service/     # Engine Gợi ý (Python AI)
├── crawler/        # Scraper dữ liệu tin tức
├── data/           # Thư mục chứa cơ sở dữ liệu SQLite
└── data_train/     # Dữ liệu mẫu dùng cho huấn luyện mô hình ban đầu
```

## 📝 Các Cải Tiến Mới Nhất
-   **Fix lỗi ánh xạ ID**: Đồng bộ hoàn toàn ID giữa Database và ML Service.
-   **Cải thiện thuật toán sắp xếp**: Sắp xếp điểm số gợi ý từ cao xuống thấp chính xác.
-   **Tối ưu hóa đa dạng tin tức**: Cải thiện thuật toán Diversity Penalty giúp người dùng không bị "ngợp" bởi 1 loại tin.
-   **Bổ sung Skeleton Card**: Nâng cao trải nghiệm người dùng trong thời gian chờ load tin.
Mọi thắc mắc vui lòng liên hệ email:ic.lengocthinh@gmail.com
