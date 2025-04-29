import tifffile

def load_tiff(file_path, max_frames=300):
	with tifffile.TiffFile(file_path) as tif:
		total_frames = len(tif.pages)
		skip = max(1, round(total_frames / max_frames))
		frames = [tif.pages[i].asarray() for i in range(0, total_frames, skip)]
	return frames
