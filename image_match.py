import cv2
import numpy as np
import os

def load_image(path):
    """Load an image from the specified file path and convert it to grayscale."""
    image = cv2.imread(path)
    if image is None:
        raise FileNotFoundError(f"Image at path {path} not found.")
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray_image

def detect_and_compute(image):
    """Detect key points and compute descriptors using ORB."""
    orb = cv2.ORB_create()
    keypoints, descriptors = orb.detectAndCompute(image, None)
    return keypoints, descriptors

def match_descriptors(descriptors1, descriptors2):
    """Match descriptors using BFMatcher."""
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(descriptors1, descriptors2)
    matches = sorted(matches, key=lambda x: x.distance)
    return matches

def verify_fingerprints(image1, image2, match_threshold=30):
    """Verify if two fingerprint images match."""
    # Detect key points and compute descriptors
    keypoints1, descriptors1 = detect_and_compute(image1)
    keypoints2, descriptors2 = detect_and_compute(image2)
    
    # Match descriptors
    matches = match_descriptors(descriptors1, descriptors2)
    
    # Determine if fingerprints match based on the number of good matches
    good_matches = [m for m in matches if m.distance < 57]  # You can adjust the distance threshold
    if len(good_matches) > match_threshold:
        return True, len(good_matches)
    else:
        return False, len(good_matches)

def match_fingerprints_in_directory(directory_path):
    """Match all fingerprint images in a directory."""
    image_files = os.listdir(directory_path)
    matched_images = []
    
    # Iterate through each pair of images
    for i in range(len(image_files)):
        for j in range(i + 1, len(image_files)):
            image_path1 = os.path.join(directory_path, image_files[i])
            image_path2 = os.path.join(directory_path, image_files[j])
            
            try:
                image1 = load_image(image_path1)
                image2 = load_image(image_path2)
                
                match, num_matches = verify_fingerprints(image1, image2)
                if match:
                    matched_images.append((image_files[i], image_files[j], num_matches))
                    
            except Exception as e:
                print(f"Error processing {image_files[i]} and {image_files[j]}: {e}")
    
    return matched_images

if __name__ == "__main__":
    directory_path = "./fingerprints"
    matched_images = match_fingerprints_in_directory(directory_path)
    
    if matched_images:
        print("Matched fingerprint pairs:")
        for image1, image2, num_matches in matched_images:
            print(f"{image1} and {image2} match with {num_matches} good matches.")
    else:
        print("No matching fingerprints found.")
