from ai_camera import IMX500Detector
import time

camera = IMX500Detector()

# Start the detector with preview window
camera.start(show_preview=True)

camera.set_zone(100,100,100,100)


# Main loop
while True:
    # Get the latest detections
    detections = camera.get_detections()
    
    # Get the labels for reference
    labels = camera.get_labels()
    
    # Process each detection
    for detection in detections:
        label = labels[int(detection.category)]
        confidence = detection.conf
        x, y, w, h = detection.box
        
        # Example: Print when a person is detected with high confidence
        if label == "bottle" and confidence > 0.4:
            print(f"bottle is in danger!")
    
    # Small delay to prevent overwhelming the system
    time.sleep(0.1)
