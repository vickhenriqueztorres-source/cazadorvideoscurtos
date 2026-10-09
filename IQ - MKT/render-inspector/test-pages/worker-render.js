const canvas = new OffscreenCanvas(256, 128);
const ctx = canvas.getContext("2d");
ctx.fillStyle = "#fff";
ctx.font = "20px Arial";
ctx.fillText("Worker text", 20, 50);
setInterval(() => {}, 1000);
