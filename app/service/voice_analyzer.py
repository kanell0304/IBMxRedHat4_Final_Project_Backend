import pickle
import torch
import torchaudio
import librosa
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import warnings

from app.core.model_loader import MODEL_DIR

warnings.filterwarnings('ignore')

class VoiceAnalyzer:
    def __init__(self, model_dir: str = "app/ml_models"):

        self.model_dir = Path(model_dir)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 모델 로드
        self._load_models()

        print(f"VoiceAnalyzer 초기화 완료 (device: {self.device})")

    def _load_models(self):
        try:
            # 감정 분류 모델 가중치 로드
            with open(self.model_dir / 'emotion_classifier.pkl', 'rb') as f:
                self.emotion_model = pickle.load(f)

            # 스케일러 로드
            with open(self.model_dir / 'scaler.pkl', 'rb') as f:
                self.scaler = pickle.load(f)

            # 레이블 매핑 로드
            with open(self.model_dir / 'label_mapping.pkl', 'rb') as f:
                label_mapping = pickle.load(f)
                self.idx_to_emotion = label_mapping['idx_to_emotion']
                self.emotion_to_idx = label_mapping['emotion_to_idx']

            # Wav2Vec2 모델 로드
            print("Wav2Vec2 모델 로드 중...")
            bundle = torchaudio.pipelines.WAV2VEC2_XLSR_300M
            self.wav2vec_model = bundle.get_model().to(self.device)
            self.wav2vec_model.eval()
            self.sample_rate = bundle.sample_rate

            print(f"  감정 클래스: {list(self.idx_to_emotion.values())}")

        except Exception as e:
            raise Exception(f"모델 로드 실패: {e}")

    def extract_wav2vec_features(self, audio_path: str) -> Optional[np.ndarray]:

        try:
            # librosa로 오디오 로드 (16kHz)
            waveform_np, sr = librosa.load(audio_path, sr=16000, mono=True)

            # numpy → torch tensor 변환
            waveform = torch.from_numpy(waveform_np).float()
            waveform = waveform.unsqueeze(0)
            waveform = waveform.to(self.device)

            # 모델 실행
            with torch.no_grad():
                features, _ = self.wav2vec_model(waveform)

            # 평균 풀링: (1, time_steps, 1024) → (1024,)
            features_mean = features.mean(dim=1).squeeze().cpu().numpy()

            return features_mean

        except Exception as e:
            print(f"Wav2Vec2 특징 추출 오류: {e}")
            return None

    def analyze_speech_features(self, audio_path: str, estimated_syllables: Optional[int] = None) -> Dict:
        try:
            # 오디오 로드
            y, sr = librosa.load(audio_path, sr=16000, mono=True)
            duration = len(y) / sr

            # 음량 (RMS Energy)
            rms = librosa.feature.rms(y=y)[0]
            avg_volume = np.mean(rms)
            max_volume = np.max(rms)
            avg_volume_db = librosa.amplitude_to_db(np.array([avg_volume]))[0]
            max_volume_db = librosa.amplitude_to_db(np.array([max_volume]))[0]

            # 피치 분석
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr, fmin=50, fmax=400)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)

            avg_pitch = np.mean(pitch_values) if pitch_values else 0
            pitch_std = np.std(pitch_values) if pitch_values else 0
            pitch_range = (np.max(pitch_values) - np.min(pitch_values)) if pitch_values else 0

            # 침묵 구간 검출 - 음성 총 길이에서 목소리가 나는 구간을 뺀 나머지 = 침묵 구간
            intervals = librosa.effects.split(y, top_db=30)
            total_speech_time = sum((end - start) / sr for start, end in intervals)
            silence_duration = duration - total_speech_time
            silence_ratio = silence_duration / duration if duration > 0 else 0

            # 발화 속도 - 말하기(단어당) 속도
            if estimated_syllables:
                speech_rate_total = estimated_syllables / duration
                speech_rate_actual = estimated_syllables / total_speech_time if total_speech_time > 0 else 0
            else:
                speech_rate_total = None
                speech_rate_actual = None

            # 기타 특징
            energy_std = np.std(rms) # 에너지 표준편차
            zcr = librosa.feature.zero_crossing_rate(y)[0] # 영교차율 -> 쉽게 말해서 음성의 파형이 0을 기준으로 얼마나 많이 왔다갔다 하는지 -> 발음이 얼마나 명확한지
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0] # 목소리가 얼마나 밝은지 정도
            num_segments = len(intervals) # 얼마나 말을 잘 끊어서 말했는지
            avg_segment_length = total_speech_time / num_segments if num_segments > 0 else 0 # 평균 세그먼트 길이

            return {
                'duration': float(duration),
                'duration_min': float(duration / 60),
                'total_speech_time': float(total_speech_time),
                'silence_duration': float(silence_duration),
                'silence_ratio': float(silence_ratio),
                'avg_volume_db': float(avg_volume_db),
                'max_volume_db': float(max_volume_db),
                'avg_pitch': float(avg_pitch),
                'pitch_std': float(pitch_std),
                'pitch_range': float(pitch_range),
                'speech_rate_total': float(speech_rate_total) if speech_rate_total else None,
                'speech_rate_actual': float(speech_rate_actual) if speech_rate_actual else None,
                'num_segments': int(num_segments),
                'avg_segment_length': float(avg_segment_length),
                'energy_std': float(energy_std),
                'avg_zcr': float(np.mean(zcr)),
                'spectral_centroid': float(np.mean(spectral_centroids))
            }

        except Exception as e:
            print(f"음성 특징 분석 오류: {e}")
            return {}

    def analyze(self, audio_path: str, estimated_syllables: Optional[int] = None) -> Dict:

        try:
            # Wav2Vec2 특징 추출
            wav2vec_features = self.extract_wav2vec_features(audio_path)

            if wav2vec_features is None:
                return {"error": "특징 추출 실패"}

            # 특징 스케일링
            features_scaled = self.scaler.transform([wav2vec_features])

            # 전체 감정 예측
            emotion_pred = self.emotion_model.predict(features_scaled)[0]
            emotion_name = self.idx_to_emotion[emotion_pred]

            # 확률 예측
            if hasattr(self.emotion_model, 'predict_proba'):
                emotion_proba = self.emotion_model.predict_proba(features_scaled)[0]

                # 전체 감정별 확률
                all_emotion_scores = {self.idx_to_emotion[i]: float(prob * 100) for i, prob in enumerate(emotion_proba)}

                # Anxious(긴장)와 Embarrassed(당황)만 추출
                target_emotions = ['Anxious', 'Embarrassed']
                filtered_scores = {}

                for emotion in target_emotions:
                    if emotion in all_emotion_scores:
                        filtered_scores[emotion] = all_emotion_scores[emotion]

                # 두 감정의 합으로 정규화 (합이 100%가 되도록) -> 6개에서 2개로 줄였으니까
                total = sum(filtered_scores.values())
                if total > 0:
                    emotion_scores = {k: (v / total) * 100 for k, v in filtered_scores.items()}
                else:
                    emotion_scores = filtered_scores

                # 주요 감정 결정 (Anxious vs Embarrassed 중 높은 것)
                if emotion_scores:
                    main_emotion = max(emotion_scores.items(), key=lambda x: x[1])
                    emotion_name = main_emotion[0]
                    emotion_confidence = main_emotion[1]
                else:
                    emotion_confidence = None
            else:
                emotion_confidence = None
                emotion_scores = None

            # 음향 특징 분석
            speech_features = self.analyze_speech_features(audio_path, estimated_syllables)

            # 결과 통합
            result = {
                'emotion': emotion_name,
                'emotion_confidence': emotion_confidence,
                'emotion_scores': emotion_scores,
                **speech_features
            }

            return result

        except Exception as e:
            print(f"분석 오류: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

_analyzer_instance = None

def get_analyzer() -> VoiceAnalyzer:
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = VoiceAnalyzer(model_dir=str(MODEL_DIR))
    return _analyzer_instance