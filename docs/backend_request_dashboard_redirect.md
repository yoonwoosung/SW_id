# 백엔드 수정 요청 — `detailed_farmer_dashboard` 제거

## 요청 배경

구 농장주 대시보드(`my_farm.html` / `/my_farm_detailed`)를 완전히 제거합니다.
현재 농장주 메인 페이지는 `farmer_easy_mode` (`/farmer_easy_mode`)로 통일되어 있으며,
구 대시보드는 더 이상 사용하지 않습니다.

---

## 수정 대상

### 1. `routes/farm.py` — line 36 · 리다이렉트 변경

```python
# 현재
return redirect(url_for('detailed_farmer_dashboard'))

# 변경
return redirect(url_for('farmer_easy_mode'))
```

### 2. `routes/reservation.py` — line 129 · 리다이렉트 변경

```python
# 현재
return redirect(url_for('detailed_farmer_dashboard'))

# 변경
return redirect(url_for('farmer_easy_mode'))
```

### 3. `routes/farm.py` — line 42, 170 · 라우트 삭제

아래 함수 및 URL 룰을 완전히 삭제해 주세요.

```python
# line 42 — 함수 전체 삭제
def detailed_farmer_dashboard():
    ...

# line 170 — URL 룰 삭제
app.add_url_rule('/my_farm_detailed', 'detailed_farmer_dashboard', detailed_farmer_dashboard)
```

### 4. 프론트엔드 — 이미 완료

`templates/my_farm.html` 은 프론트에서 보관만 하고 어떤 링크도 연결되어 있지 않습니다.
백엔드 라우트 삭제 후 해당 파일도 함께 삭제해도 됩니다.

---

## 요약

| 파일 | 위치 | 작업 |
|---|---|---|
| `routes/farm.py` | line 36 | 리다이렉트 대상 변경 |
| `routes/reservation.py` | line 129 | 리다이렉트 대상 변경 |
| `routes/farm.py` | line 42, 170 | 라우트 함수 및 URL 룰 삭제 |
| `templates/my_farm.html` | — | 라우트 삭제 후 파일 삭제 가능 |
