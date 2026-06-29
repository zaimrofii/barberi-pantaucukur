import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Save, Loader2 } from "lucide-react";
import { cn } from "../components/lib/utils";

const API_BASE = "http://127.0.0.1:8000/api";

export default function ROLEditor() {
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const [frame, setFrame] = useState(null);
  const [rois, setRois] = useState([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState(null);
  const [currentPoint, setCurrentPoint] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  // Fetch camera frame
  const fetchFrame = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/camera/frame/`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.status !== "success") throw new Error(data.message || "Unknown error");
      setFrame(data.frame);
      setRois(data.rois || []);
      setImageLoaded(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFrame();
  }, [fetchFrame]);

  // Draw canvas when frame or rois change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !frame) return;
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.onload = () => {
      // Set canvas size to image natural size
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);
      setImageLoaded(true);
      drawRois(ctx, rois);
    };
    img.src = `data:image/jpeg;base64,${frame}`;
  }, [frame, rois]);

  const drawRois = (ctx, roisList, preview = null) => {
    if (!ctx) return;
    // Redraw image first
    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0);
      // Draw existing ROIs
      roisList.forEach((roi, idx) => {
        const [x1, y1, x2, y2] = roi;
        const x = Math.min(x1, x2);
        const y = Math.min(y1, y2);
        const w = Math.abs(x2 - x1);
        const h = Math.abs(y2 - y1);
        ctx.fillStyle = "rgba(34, 197, 94, 0.2)";
        ctx.fillRect(x, y, w, h);
        ctx.strokeStyle = "rgba(34, 197, 94, 0.8)";
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);
        ctx.fillStyle = "rgba(34, 197, 94, 0.9)";
        ctx.font = "bold 14px sans-serif";
        ctx.fillText(`Kursi ${idx + 1}`, x + 4, y + 16);
      });
      // Draw preview rectangle while dragging
      if (preview) {
        const { start, current } = preview;
        const x = Math.min(start.x, current.x);
        const y = Math.min(start.y, current.y);
        const w = Math.abs(current.x - start.x);
        const h = Math.abs(current.y - start.y);
        ctx.fillStyle = "rgba(59, 130, 246, 0.2)";
        ctx.fillRect(x, y, w, h);
        ctx.strokeStyle = "rgba(59, 130, 246, 0.8)";
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(x, y, w, h);
        ctx.setLineDash([]);
      }
    };
    img.src = `data:image/jpeg;base64,${frame}`;
  };

  // Mouse handlers
  const getCanvasCoords = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  };

  const handleMouseDown = (e) => {
    if (!imageLoaded) return;
    const coords = getCanvasCoords(e);
    setIsDrawing(true);
    setStartPoint(coords);
    setCurrentPoint(coords);
  };

  const handleMouseMove = (e) => {
    if (!isDrawing) return;
    const coords = getCanvasCoords(e);
    setCurrentPoint(coords);
    // Redraw with preview
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    drawRois(ctx, rois, { start: startPoint, current: coords });
  };

  const handleMouseUp = (e) => {
    if (!isDrawing) return;
    setIsDrawing(false);
    const endPoint = getCanvasCoords(e);
    const x1 = Math.round(Math.min(startPoint.x, endPoint.x));
    const y1 = Math.round(Math.min(startPoint.y, endPoint.y));
    const x2 = Math.round(Math.max(startPoint.x, endPoint.x));
    const y2 = Math.round(Math.max(startPoint.y, endPoint.y));
    // Ignore very small rectangles
    if (Math.abs(x2 - x1) < 10 || Math.abs(y2 - y1) < 10) {
      // Redraw without preview
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext("2d");
        drawRois(ctx, rois);
      }
      return;
    }
    const newRoi = [x1, y1, x2, y2];
    const updatedRois = [...rois, newRoi];
    setRois(updatedRois);
    setStartPoint(null);
    setCurrentPoint(null);
  };

  // Save ROIs
  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/roi/update/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rois }),
      });
      const data = await res.json();
      if (data.status === "success") {
        alert("ROI berhasil disimpan!");
      } else {
        alert("Gagal menyimpan: " + (data.message || "Unknown error"));
      }
    } catch (err) {
      alert("Gagal menyimpan: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  // Delete ROI by clicking on existing rectangle (simple approach: delete last)
  const handleCanvasClick = (e) => {
    if (isDrawing) return;
    if (rois.length === 0) return;
    // Delete the last ROI for simplicity
    const updated = rois.slice(0, -1);
    setRois(updated);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-orange-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
        <p className="text-red-500 mb-4">Error: {error}</p>
        <button
          onClick={fetchFrame}
          className="px-4 py-2 bg-orange-500 text-white rounded-lg"
        >
          Coba Lagi
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="text-sm font-medium">Kembali</span>
        </button>
        <h1 className="text-lg font-bold">ROI Editor</h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all",
            saving
              ? "bg-muted text-muted-foreground cursor-not-allowed"
              : "bg-orange-500 text-white hover:bg-orange-600 active:scale-95"
          )}
        >
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          Simpan
        </button>
      </header>

      {/* Instructions */}
      <div className="px-4 py-2 text-xs text-muted-foreground">
        Klik dan seret pada gambar untuk membuat ROI. Klik pada ROI yang ada untuk menghapus ROI terakhir.
      </div>

      {/* Canvas Container */}
      <div className="flex-1 flex items-center justify-center p-4 overflow-auto">
        <div className="relative max-w-full max-h-full">
          <canvas
            ref={canvasRef}
            className="border border-white/10 rounded-lg cursor-crosshair max-w-full max-h-full"
            style={{ width: "100%", height: "auto" }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={() => {
              if (isDrawing) {
                setIsDrawing(false);
                const canvas = canvasRef.current;
                if (canvas) {
                  const ctx = canvas.getContext("2d");
                  drawRois(ctx, rois);
                }
              }
            }}
            onClick={handleCanvasClick}
          />
          {isDrawing && (
            <div className="absolute top-2 left-2 bg-blue-500 text-white text-xs px-2 py-1 rounded">
              Drawing...
            </div>
          )}
        </div>
      </div>

      {/* ROI List */}
      <div className="px-4 py-3 border-t border-white/10">
        <h2 className="text-sm font-semibold mb-2">Daftar ROI ({rois.length})</h2>
        <div className="flex flex-wrap gap-2">
          {rois.map((roi, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-2 py-1 bg-green-500/10 text-green-400 text-xs rounded-full"
            >
              Kursi {idx + 1}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
