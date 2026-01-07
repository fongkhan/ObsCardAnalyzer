from flask import Flask, render_template, jsonify, Response
from flask_cors import CORS
import cv2
import time
import atexit
from detector import CardDetector

app = Flask(__name__)
CORS(app)

# Initialize Detector (Camera 0 by default)
detector = CardDetector(camera_index=0)
detector.start()

# Cleanup on exit
def cleanup():
    detector.stop()

atexit.register(cleanup)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/current_card')
def get_current_card():
    # Return JSON of current card info
    return jsonify(detector.current_card_info)

@app.route('/video_feed')
def video_feed():
    """
    Video streaming route. Put this in the src attribute of an img tag.
    """
    def generate():
        while True:
            # Use processed frame if available (shows contours)
            if detector.processed_frame is not None:
                frame = detector.processed_frame
            elif detector.current_frame is not None:
                frame = detector.current_frame
            else:
                time.sleep(0.1)
                continue
            
            # Encode as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.03) # Limit FPS

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Run with threaded=True so the main thread isn't blocked? 
    # Actually Flask run is blocking, but detector is in its own thread.
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
