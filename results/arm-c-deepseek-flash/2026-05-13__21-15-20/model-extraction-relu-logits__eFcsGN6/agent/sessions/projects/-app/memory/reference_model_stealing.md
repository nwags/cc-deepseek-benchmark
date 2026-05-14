---
name: reference-model-stealing
description: Technique for extracting weight matrix from a one-layer ReLU network via gradient jump detection
metadata: 
  node_type: memory
  type: reference
  originSessionId: e5f0471d-ac66-4c63-a6b0-2fd636c6953d
---

Model stealing from a one-layer ReLU network `f(x) = A2 @ ReLU(A1 @ x + b1) + b2`:

The gradient ∇f(x) is piecewise constant, jumping by ±A2[i]·A1[i,:] at each neuron's activation boundary. By scanning along random lines passing near the origin (keeps kinks within scan range), detecting kinks via second differences, computing the gradient change (finite differences) at each kink, and clustering the resulting direction vectors, you can recover all rows of A1 up to per-neuron scaling and permutation.

Key details:
- Use origin (x0=0) as reference point to keep kinks within scan range
- Each kink produces two adjacent non-zero second-difference values — merge them
- Close kinks (< 0.005 apart) produce merged gradient changes; use frequency-based clustering to select the h most common (pure) directions
- 4000-sample scans over [-10, 10] with 50 random directions works for a 20-neuron hidden layer
