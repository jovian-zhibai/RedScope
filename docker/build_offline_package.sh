#!/bin/bash
# ============================================================
# RedScope 离线部署包生成脚本
# 用法: bash build_offline_package.sh
# 输出: redscope-offline-<日期>.tar.gz
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="/tmp/redscope-offline-build"
DATE=$(date +%Y%m%d)
PACKAGE_NAME="redscope-offline-${DATE}"

echo "============================================"
echo "  RedScope 离线部署包构建"
echo "============================================"
echo ""

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/$PACKAGE_NAME"

echo "[1/6] 复制项目文件..."
cp -r "$PROJECT_DIR/backend" "$BUILD_DIR/$PACKAGE_NAME/"
cp -r "$PROJECT_DIR/frontend" "$BUILD_DIR/$PACKAGE_NAME/"
cp -r "$PROJECT_DIR/plugins" "$BUILD_DIR/$PACKAGE_NAME/"
cp -r "$PROJECT_DIR/pipelines" "$BUILD_DIR/$PACKAGE_NAME/"
cp -r "$PROJECT_DIR/docker" "$BUILD_DIR/$PACKAGE_NAME/"
cp "$PROJECT_DIR/docker-compose.yml" "$BUILD_DIR/$PACKAGE_NAME/"

echo "[2/6] 构建前端..."
cd "$PROJECT_DIR/frontend"
npm ci && npm run build
cp -r dist "$BUILD_DIR/$PACKAGE_NAME/frontend/"

echo "[3/6] 导出 Docker 镜像..."
mkdir -p "$BUILD_DIR/$PACKAGE_NAME/images"

# Build project images
cd "$PROJECT_DIR"
docker-compose build

# Save project images
docker save redscope-backend:latest -o "$BUILD_DIR/$PACKAGE_NAME/images/backend.tar"
docker save redscope-frontend:latest -o "$BUILD_DIR/$PACKAGE_NAME/images/frontend.tar"

# Save dependency images
echo "  拉取并导出依赖镜像..."
IMAGES=(
    "postgres:16-alpine"
    "redis:7-alpine"
    "instrumentisto/nmap:7.95"
    "projectdiscovery/nuclei:v3.3.8"
    "projectdiscovery/subfinder:v2.6.7"
    "projectdiscovery/httpx:v1.6.9"
    "paoloo/sqlmap:latest"
    "cyal1/dirsearch:latest"
)

for img in "${IMAGES[@]}"; do
    echo "  → $img"
    docker pull "$img" 2>/dev/null || true
    filename=$(echo "$img" | tr '/:' '_')
    docker save "$img" -o "$BUILD_DIR/$PACKAGE_NAME/images/${filename}.tar"
done

echo "[4/6] 导出漏洞情报库快照..."
mkdir -p "$BUILD_DIR/$PACKAGE_NAME/data"
# Export database if running
docker-compose exec -T db pg_dump -U redscope redscope > "$BUILD_DIR/$PACKAGE_NAME/data/vuln_db_snapshot.sql" 2>/dev/null || echo "  (数据库未运行,跳过快照)"

echo "[5/6] 生成离线安装脚本..."
cat > "$BUILD_DIR/$PACKAGE_NAME/install.sh" << 'INSTALL_EOF'
#!/bin/bash
# RedScope 离线安装脚本
set -e

echo "============================================"
echo "  RedScope 离线安装"
echo "============================================"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 未检测到Docker,请先安装Docker"
    echo "   离线安装Docker: 将docker-ce包拷贝到本机后 dpkg -i 或 rpm -i 安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ 未检测到docker-compose,请先安装"
    exit 1
fi

echo "[1/3] 导入Docker镜像..."
for img_file in images/*.tar; do
    echo "  → 导入 $(basename $img_file)"
    docker load -i "$img_file"
done

echo "[2/3] 导入漏洞数据库快照..."
if [ -f "data/vuln_db_snapshot.sql" ]; then
    # Will be imported after DB starts
    echo "  数据库快照准备就绪,启动后自动导入"
    cp data/vuln_db_snapshot.sql docker/init.sql
fi

echo "[3/3] 启动 RedScope..."
docker-compose up -d

echo ""
echo "============================================"
echo "  ✅ RedScope 安装完成!"
echo ""
echo "  访问地址: http://localhost:3000"
echo "  API地址:  http://localhost:8000"
echo "  默认账号: 首次访问请注册"
echo "============================================"
INSTALL_EOF

chmod +x "$BUILD_DIR/$PACKAGE_NAME/install.sh"

# Readme
cat > "$BUILD_DIR/$PACKAGE_NAME/README.txt" << 'README_EOF'
RedScope 离线部署包
==================

使用方法:
1. 确保目标机器已安装 Docker 和 docker-compose
2. 解压本包: tar -xzf redscope-offline-YYYYMMDD.tar.gz
3. 进入目录: cd redscope-offline-YYYYMMDD
4. 执行安装: bash install.sh
5. 浏览器打开: http://localhost:3000

包含内容:
- RedScope 平台完整代码
- 所有依赖的 Docker 镜像 (无需联网)
- 预置扫描工具 (nmap/nuclei/subfinder/httpx/sqlmap/dirsearch)
- 漏洞情报库快照
- 等保基线检查模板

系统要求:
- Docker 20.10+
- docker-compose 2.0+
- 磁盘空间 >= 10GB
- 内存 >= 4GB
README_EOF

echo "[6/6] 打包..."
cd "$BUILD_DIR"
tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
mv "${PACKAGE_NAME}.tar.gz" "$PROJECT_DIR/"

SIZE=$(du -sh "$PROJECT_DIR/${PACKAGE_NAME}.tar.gz" | awk '{print $1}')
echo ""
echo "============================================"
echo "  ✅ 离线部署包构建完成!"
echo "  文件: ${PACKAGE_NAME}.tar.gz"
echo "  大小: $SIZE"
echo "  拷贝到U盘后在目标机器执行 install.sh 即可"
echo "============================================"

# Cleanup
rm -rf "$BUILD_DIR"
