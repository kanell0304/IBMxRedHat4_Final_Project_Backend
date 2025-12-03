import boto3
import os
from pathlib import Path
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError
load_dotenv()

# 모델 파일 경로
MODEL_DIR = Path(__file__).parent.parent / "ml_models"

# S3 설정
S3_BUCKET = os.getenv("S3_MODEL_BUCKET", "")
S3_MODEL_PREFIX = os.getenv("S3_MODEL_PREFIX", "models/")

# 관리할 모델 파일 목록
MODEL_FILES = [
    "emotion_classifier.pkl", # 가중치 파일
    "scaler.pkl", # 정규화 데이터
    "label_mapping.pkl" # 라벨 매핑 데이터
]


def is_s3_enabled() -> bool:
    return bool(S3_BUCKET)


def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "ap-northeast-2")
    )


def check_local_models() -> dict:
    status = {}
    for model_name in MODEL_FILES:
        local_path = MODEL_DIR / model_name
        status[model_name] = local_path.exists()
    return status


def download_model_from_s3(model_name: str, force: bool = False) -> bool:
    local_path = MODEL_DIR / model_name
    s3_key = f"{S3_MODEL_PREFIX}{model_name}"

    if local_path.exists() and not force:
        print(f"  {model_name} 이미 존재 (스킵)")
        return True

    try:
        s3 = get_s3_client()
        print(f"  {model_name} S3에서 다운로드 중...")

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        s3.download_file(S3_BUCKET, s3_key, str(local_path))

        size_mb = local_path.stat().st_size / (1024 * 1024)
        print(f"  {model_name} 완료 ({size_mb:.1f} MB)")
        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"  {model_name} S3에 없음")
        else:
            print(f"  {model_name} 다운로드 실패: {e}")
        return False
    except NoCredentialsError:
        print(f"  AWS 자격 증명 없음")
        return False
    except Exception as e:
        print(f"  {model_name} 오류: {e}")
        return False


def download_all_models_from_s3(force: bool = False) -> bool:
    print(f"  버킷: {S3_BUCKET}")
    print(f"  경로: {S3_MODEL_PREFIX}")

    success_count = 0
    for model_name in MODEL_FILES:
        if download_model_from_s3(model_name, force):
            success_count += 1

    return success_count == len(MODEL_FILES)


def ensure_models_ready() -> bool:

    # 로컬 파일 확인
    local_status = check_local_models()
    all_local = all(local_status.values())
    missing = [name for name, exists in local_status.items() if not exists]

    if all_local:
        print("모든 모델 파일이 로컬에 존재합니다.")
        for name in MODEL_FILES:
            size_mb = (MODEL_DIR / name).stat().st_size / (1024 * 1024)
            print(f"  {name} ({size_mb:.1f} MB)")
        return True

    # 로컬에 없는 파일이 있음
    print(f"누락된 파일: {missing}")

    # S3 설정 확인
    if not is_s3_enabled():
        print("")
        print("S3 설정이 없습니다.")
        print("   로컬 파일을 직접 배치하거나 .env에 S3 설정을 추가하세요:")
        print("   - S3_MODEL_BUCKET=your-bucket-name")
        print("   - AWS_ACCESS_KEY_ID=your-key")
        print("   - AWS_SECRET_ACCESS_KEY=your-secret")
        return False

    # S3에서 다운로드
    print("")
    print("S3에서 다운로드 시도...")
    success = download_all_models_from_s3()

    if success:
        print("")
        print("모든 모델 다운로드 완료!")
    else:
        print("")
        print("일부 모델 다운로드 실패")

    return success


def upload_model_to_s3(model_name: str) -> bool:
    if not is_s3_enabled():
        print("S3 설정이 없습니다. .env에 S3_MODEL_BUCKET을 설정하세요.")
        return False

    local_path = MODEL_DIR / model_name
    s3_key = f"{S3_MODEL_PREFIX}{model_name}"

    if not local_path.exists():
        print(f"{model_name} 로컬에 없음")
        return False

    try:
        s3 = get_s3_client()
        size_mb = local_path.stat().st_size / (1024 * 1024)
        print(f"⬆ {model_name} 업로드 중 ({size_mb:.1f} MB)...")

        s3.upload_file(str(local_path), S3_BUCKET, s3_key)

        print(f"업로드 완료: s3://{S3_BUCKET}/{s3_key}")
        return True

    except Exception as e:
        print(f"업로드 실패: {e}")
        return False


def upload_all_models() -> bool:
    print("S3에 모델 업로드")

    success_count = 0
    for model_name in MODEL_FILES:
        if upload_model_to_s3(model_name):
            success_count += 1

    print(f"완료: {success_count}/{len(MODEL_FILES)} 파일")

    return success_count == len(MODEL_FILES)


# CLI 실행
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법: python -m app.core.model_loader [check|download|upload]")
        print("")
        print("  check    - 로컬 모델 파일 확인")
        print("  download - S3에서 모델 다운로드")
        print("  upload   - 로컬 모델을 S3에 업로드")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        ensure_models_ready()
    elif command == "download":
        if is_s3_enabled():
            download_all_models_from_s3(force="--force" in sys.argv)
        else:
            print("S3 설정이 없습니다.")
    elif command == "upload":
        upload_all_models()
    else:
        print(f"알 수 없는 명령: {command}")