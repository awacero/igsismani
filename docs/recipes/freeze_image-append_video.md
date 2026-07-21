## freeze and image for X seconds 

```python
...

        """        
        
        ##Keep information displayed for 3 segoncds 
        hold_frames = runtime["fps"] * 3
        if frame_array:
            last_frame = frame_array[-1].copy()
            for _ in range(hold_frames):
                frame_array.append(last_frame.copy())
```


## use short video for outro

```python
...

        ## Remover el outro y remplazar x un video corto
        '''
        outro_img = cv2.imread(f"{runtime['frames_out']}/outro_qr.png")
        outro_img = cv2.resize(outro_img,(size[0],size[1]))

        for _ in range(runtime["fps"] *2):
            frame_array.append(outro_img)

        '''
        outro_video_path = f"{runtime['frames_out']}/outro_xs.mp4"
        cap

``` 

