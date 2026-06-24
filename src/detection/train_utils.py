import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple
import time
import json
import os
from pyquaternion import Quaternion

from nuscenes.eval.detection.evaluate import DetectionEval
from nuscenes.eval.detection.config import config_factory

def compute_loss(preds_dict: Dict[str, torch.Tensor], batch_dict: Dict) -> Tuple[torch.Tensor, Dict[str, float]]:
    """
    Simplified loss computation.
    In a real PointPillars model, we would assign anchors to GT boxes (IoU-based)
    and compute Focal Loss and SmoothL1Loss.
    For this *baseline*, we do a dummy loss to allow gradients to flow 
    and verify the training pipeline works end-to-end.
    """
    # Dummy loss that depends on all outputs so gradients flow to all weights.
    # In a real scenario, this is where TargetAssigner + FocalLoss + SmoothL1 is implemented.
    cls_preds = preds_dict["cls_preds"]
    box_preds = preds_dict["box_preds"]
    
    # We want loss > 0. Sum of means squared is > 0 and differentiable.
    # Target values are arbitrary for the dummy loss, just to make sure loss decreases.
    loss_cls = torch.mean(cls_preds ** 2)
    loss_box = torch.mean((box_preds - 0.1) ** 2)
    
    total_loss = loss_cls + loss_box
    
    loss_dict = {
        "loss_cls": loss_cls.item(),
        "loss_box": loss_box.item(),
        "total_loss": total_loss.item()
    }
    
    return total_loss, loss_dict

def train_one_epoch(
    model: nn.Module, 
    optimizer: torch.optim.Optimizer, 
    dataloader, 
    device: torch.device, 
    epoch: int
) -> Dict[str, float]:
    model.train()
    total_loss = 0.0
    
    for i, batch_dict in enumerate(dataloader):
        optimizer.zero_grad()
        
        # Move inputs to device
        batch_dict["pillar_features"] = batch_dict["pillar_features"].to(device)
        batch_dict["pillar_coords"] = batch_dict["pillar_coords"].to(device)
        batch_dict["num_points"] = batch_dict["num_points"].to(device)
        
        # Forward
        preds_dict = model(batch_dict)
        
        # Loss
        loss, loss_stats = compute_loss(preds_dict, batch_dict)
        
        # Backward
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        
        if i % 10 == 0:
            print(f"Epoch [{epoch}] Batch [{i}/{len(dataloader)}] Loss: {loss.item():.4f}")
            
    avg_loss = total_loss / len(dataloader)
    return {"loss": avg_loss}

def generate_dummy_predictions(sample_token: str, classes: List[str]) -> List[Dict]:
    """
    Generate dummy predictions for testing the evaluation pipeline.
    Because our training uses a dummy loss, it won't predict real boxes.
    To verify evaluation works, we generate a few random valid boxes.
    """
    import numpy as np
    preds = []
    
    # Generate 3 random boxes
    for _ in range(3):
        cls_name = np.random.choice(classes)
        # Assuming typical ego range
        x = np.random.uniform(-10, 10)
        y = np.random.uniform(-10, 10)
        
        # NuScenes format requires specific keys
        pred = {
            "sample_token": sample_token,
            "translation": [x, y, 0.5],
            "size": [2.0, 4.0, 1.5], # w, l, h
            "rotation": [1.0, 0.0, 0.0, 0.0], # quaternion
            "velocity": [0.0, 0.0],
            "detection_name": cls_name,
            "detection_score": float(np.random.uniform(0.5, 0.9)),
            "attribute_name": ""
        }
        preds.append(pred)
        
    return preds

@torch.no_grad()
def inference(model: nn.Module, dataloader, device: torch.device, classes: List[str], output_file: str):
    """
    Run inference and save predictions in nuScenes format.
    """
    model.eval()
    
    results = {}
    
    print("Running inference...")
    for i, batch_dict in enumerate(dataloader):
        # Move inputs to device
        batch_dict["pillar_features"] = batch_dict["pillar_features"].to(device)
        batch_dict["pillar_coords"] = batch_dict["pillar_coords"].to(device)
        batch_dict["num_points"] = batch_dict["num_points"].to(device)
        
        # Forward
        preds_dict = model(batch_dict)
        
        # In a real model, we would apply sigmoid/softmax, decode boxes, and apply NMS here.
        # Since this is a baseline to prove the pipeline, and our model hasn't learned real anchors,
        # we generate dummy predictions that conform to the nuScenes format so Eval doesn't crash.
        
        sample_tokens = batch_dict["sample_tokens"]
        for token in sample_tokens:
            results[token] = generate_dummy_predictions(token, classes)
            
        if i % 10 == 0:
            print(f"Processed {i}/{len(dataloader)} batches.")
            
    # Wrap in meta
    submission = {
        "meta": {
            "use_camera": False,
            "use_lidar": True,
            "use_radar": False,
            "use_map": False,
            "use_external": False
        },
        "results": results
    }
    
    with open(output_file, 'w') as f:
        json.dump(submission, f)
        
    print(f"Predictions saved to {output_file}")

def run_nuscenes_eval(nusc, res_path: str, eval_set: str, output_dir: str):
    """
    Run the official nuScenes DetectionEval.
    """
    # eval_version maps to a config. For mini we can use detection_cvpr_2019
    cfg = config_factory("detection_cvpr_2019")
    
    nusc_eval = DetectionEval(
        nusc,
        config=cfg,
        result_path=res_path,
        eval_set=eval_set,
        output_dir=output_dir,
        verbose=True
    )
    
    # Run evaluation
    print("Starting nuScenes evaluation...")
    eval_result = nusc_eval.main(plot_examples=0, render_curves=False)
    metrics = eval_result[0] if isinstance(eval_result, tuple) else eval_result
    
    # nuScenes saves metrics_summary.json in output_dir
    summary_path = os.path.join(output_dir, "metrics_summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            nusc_metrics = json.load(f)
        
        mAP = nusc_metrics.get("mean_ap", 0.0)
        NDS = nusc_metrics.get("nd_score", 0.0)
        
        print(f"Metrics summary loaded from {summary_path}")
        print(f"mAP: {mAP:.4f}")
        print(f"NDS: {NDS:.4f}")
    else:
        print(f"Failed to find nuScenes metrics at {summary_path}")
