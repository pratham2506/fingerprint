import cv2
import numpy as np
import matplotlib.pyplot as plt
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
    orb = cv2.ORB_create(nfeatures=1500)
    keypoints, descriptors = orb.detectAndCompute(image, None)
    return keypoints, descriptors

def match_descriptors(descriptors1, descriptors2):
    """Match descriptors using BFMatcher with a ratio test."""
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = bf.knnMatch(descriptors1, descriptors2, k=2)
    
    # Apply ratio test
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)
    return good_matches

def verify_fingerprints(image1, image2, min_match_count=10):
    """Verify if two fingerprint images match."""
    # Detect key points and compute descriptors
    keypoints1, descriptors1 = detect_and_compute(image1)
    keypoints2, descriptors2 = detect_and_compute(image2)
    
    if descriptors1 is None or descriptors2 is None:
        return False, 0
    
    # Match descriptors
    matches = match_descriptors(descriptors1, descriptors2)
    
    # Ensure there are enough matches
    if len(matches) > min_match_count:
        # Extract location of good matches
        src_pts = np.float32([keypoints1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([keypoints2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        # Compute homography using RANSAC
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        matches_mask = mask.ravel().tolist()
        
        # Verify the match using the homography matrix
        if M is not None and sum(matches_mask) > min_match_count:
            out = cv2.drawMatches(image1, keypoints1, image2, keypoints2, matches, None, 
                                  matchesMask=matches_mask, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
            plt.imshow(out)
            plt.show()
            return True, sum(matches_mask)
    return False, 0

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
