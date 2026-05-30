from .base import BaseTranslator


class OptimizerTranslator(BaseTranslator):
    node_type = "optimizer"

    def optimizer_code(self, writer):
        opt = self.node
        loss_map = {
            "cross_entropy": "nn.CrossEntropyLoss()",
            "mse": "nn.MSELoss()",
            "bce": "nn.BCELoss()",
            "nll": "nn.NLLLoss()",
            "l1": "nn.L1Loss()",
            "huber": "nn.HuberLoss()",
        }
        loss_fn = loss_map.get(opt.get("lossType"), "nn.CrossEntropyLoss()")
        writer.line(f"loss_fn = {loss_fn}")

        opt_type = opt.get("optimizerType", "adam")
        lr = opt.get("learningRate", 0.001)

        if opt_type == "adam":
            b1 = opt.get("adamBeta1", 0.9)
            b2 = opt.get("adamBeta2", 0.999)
            eps = opt.get("adamEpsilon", 1e-8)
            writer.line(
                f"optimizer = optim.Adam(model.parameters(), lr={lr}, betas=({b1}, {b2}), eps={eps})"
            )
        elif opt_type == "adamw":
            b1 = opt.get("adamBeta1", 0.9)
            b2 = opt.get("adamBeta2", 0.999)
            eps = opt.get("adamEpsilon", 1e-8)
            wd = opt.get("weightDecay", 0)
            writer.line(
                f"optimizer = optim.AdamW(model.parameters(), lr={lr}, betas=({b1}, {b2}), eps={eps}, weight_decay={wd})"
            )
        elif opt_type == "sgd":
            mom = opt.get("sgdMomentum", 0.9)
            wd = opt.get("weightDecay", 0)
            nesterov = ", nesterov=True" if opt.get("nesterov") else ""
            writer.line(
                f"optimizer = optim.SGD(model.parameters(), lr={lr}, momentum={mom}, weight_decay={wd}{nesterov})"
            )
