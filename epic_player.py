import cv2, argparse
from glob import glob 
import pandas as pd 

class EPIC_Player:     
    #------------------------------------------------------------------------------------
    def __init__(self, db_root_dir, video_id, frame_size, vspeed):
        #load annotation files 
        self.video_id = video_id   
        self.frames_dir = db_root_dir + '/rgb/train/' + self.video_id.split('_')[0]+ '/'
        self.annotation_dir = './annotations/'
        self.videos_info = pd.read_csv(self.annotation_dir + 'EPIC_video_info.csv')
        self.video_table = pd.read_pickle(self.annotation_dir + 'per_video/'+self.video_id+'.pkl')
        self.object_table = pd.read_pickle(self.annotation_dir + 'per_video/'+self.video_id+'_objects.pkl')
 
        #initialize player options
        self.frame_size =  frame_size
        self.fps = vspeed
        self.txt_positions = {'bottom' : (30, frame_size[1]-30), 'up': (30, 30)}
        self.video_resolution = self.videos_info[self.videos_info.video == self.video_id]['resolution'].values[0].split('x')
        self.img_scale = (self.frame_size[0]/int(self.video_resolution[0]), 
                            self.frame_size[1]/int(self.video_resolution[1]))
        
        #load frames list
        self.frames_list =  sorted(glob(self.frames_dir + self.video_id + '/*'))
        print('number of found frames: ', len(self.frames_list))

    #------------------------------------------------------------------------------------
    def add_txt_frame(self, txt, txt_pos, pre_txt='', txt_scale=0.5, txt_color=(255, 255, 255)): 
        """adds txt to frame at specific position"""
        cv2.putText(self.frame, pre_txt + str(txt), txt_pos, cv2.FONT_HERSHEY_SIMPLEX, txt_scale, txt_color)

    #------------------------------------------------------------------------------------
    def draw_rect_frame(self, df_objects):
        for noun in list(df_objects.noun):
            bounding_boxes = eval(df_objects[df_objects.noun == noun].bounding_boxes.get_values()[0])
            if bounding_boxes == []: continue       
            for rect in bounding_boxes:
                (t, l, h, w) = rect
                t = int(t * self.img_scale[1])
                l = int(l * self.img_scale[0])
                h = int(h * self.img_scale[1])
                w = int(w * self.img_scale[0])
                cv2.rectangle(self.frame, (l, t), (l+w,t+h), (0, 0, 255), 1)
                self.add_txt_frame(noun, txt_pos=(l, t), txt_scale=0.3, txt_color=(0, 255, 0))

    #------------------------------------------------------------------------------------
    def framenum2uid(self, video_table, frame_num):              
        filter_start =  self.video_table[self.video_table.start_frame <= frame_num] 
        return filter_start[filter_start.stop_frame >= frame_num]

    #------------------------------------------------------------------------------------    
    def handle_keys(self):
        if chr(self.pressed_key) in [ ' ', 'S' ]: #move forward
            self.frame_ind += self.fps
        elif chr(self.pressed_key) in [ 'Q' ]: #move backward
            self.frame_ind = self.frame_ind - self.fps if self.frame_ind - self.fps > 0 else 0
        elif chr(self.pressed_key) in [ 'R' ]: #double the speed
            self.fps *= 2
        elif chr(self.pressed_key) in [ 'T' ]: #half the speed 
            self.fps = self.fps//2 if self.fps/2 > 1 else 1
    
    #------------------------------------------------------------------------------------
    def annotate_frame(self, show_actions, show_objects):
        if show_actions:
            frame_narration = self.framenum2uid(self.video_table, self.frame_ind).narration
            if len(frame_narration) > 0: 
                self.add_txt_frame(frame_narration.get_values(), pre_txt='narrations: ', txt_pos=self.txt_positions['bottom'], txt_color=(160, 208, 255)) 
        if show_objects:
            frame_objects = self.object_table[self.object_table.frame == self.frame_ind]
            if len(frame_objects) > 0: 
                self.add_txt_frame(frame_objects.noun.get_values(), pre_txt='objects: ', txt_pos=self.txt_positions['up'])
                self.draw_rect_frame(frame_objects)

    #------------------------------------------------------------------------------------
    def save_video(self, show_actions=True, show_objects=True):     
        from tqdm import tqdm   
        self.pressed_key = -1

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_video_name = self.video_id+'_with_bb.mp4'
        out_video = cv2.VideoWriter(out_video_name, fourcc, 20.0, self.frame_size)

        for self.frame_ind in tqdm(range(1, len(self.frames_list), self.fps)):            
            self.frame = cv2.imread(self.frames_list[self.frame_ind])
            self.frame =  cv2.resize(self.frame, self.frame_size)
            self.annotate_frame(show_actions, show_objects)
            out_video.write(self.frame)
        
        out_video.release()
        print("The output video is {}".format(out_video_name))

    #------------------------------------------------------------------------------------
    def play(self, show_actions=True, show_objects=True):        
        self.pressed_key = -1
        self.frame_ind = 1

        while self.pressed_key!=27:
            if self.frame_ind < len(self.frames_list):
                self.frame = cv2.imread(self.frames_list[self.frame_ind])
                self.frame =  cv2.resize(self.frame, self.frame_size)
                self.annotate_frame(show_actions, show_objects)
                cv2.imshow(video_name, self.frame)
                self.pressed_key = cv2.waitKey(0)
                self.handle_keys()
            
    #------------------------------------------------------------------------------------
        
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root_db_dir', dest='root_db_dir', type=str,
                        default='./', help='root of epic dataset')
    parser.add_argument('-vid', '--video_id', dest='video_id', type=str, 
                        help='video id example without extension ex (P01_01)')
    parser.add_argument('--mode', dest='mode', type=str, 
                        default='play', help='save or play the video')
    parser.add_argument('--vspeed', dest='vspeed', type=int, 
                        default=2, help='number of frames to skip between each 2 played frames')
    parser.add_argument('--size', dest='size', type=int, nargs=2,  
                        default=[456, 256], help='size of the frame in pixels')
    return parser.parse_args()

if __name__ == '__main__':
    
    args = get_args()

    db_root_dir = args.root_db_dir
    video_name = args.video_id
    epic_player = EPIC_Player(db_root_dir, video_name, frame_size = tuple(args.size), vspeed = args.vspeed)
    
    if args.mode == 'save':
        epic_player.save_video()
    elif args.mode == 'play':
        epic_player.play()
