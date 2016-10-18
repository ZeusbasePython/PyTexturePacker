from ..Rect import Rect

MAX_RANK = 2 ** 32


class MaxRects(object):
    """
    the max rects data
    """

    EXPAND_BOTH = 0
    EXPAND_WIDTH = 1
    EXPAND_HEIGHT = 2
    EXPAND_SHORT_SIDE = 3
    EXPAND_LONG_SIDE = 4

    def __init__(self, width=1, height=1):
        super(MaxRects, self).__init__()

        self.size = (width, height)

        self.max_rect_list = [Rect(0, 0, width, height)]
        self.image_rect_list = []

    def expand(self, method=EXPAND_BOTH):
        old_size = self.size
        if method == MaxRects.EXPAND_BOTH:
            self.size = (self.size[0] * 2, self.size[1] * 2)
        elif method == MaxRects.EXPAND_WIDTH:
            self.size = (self.size[0] * 2, self.size[1])
        elif method == MaxRects.EXPAND_HEIGHT:
            self.size = (self.size[0], self.size[1] * 2)
        elif method == MaxRects.EXPAND_SHORT_SIDE:
            if self.size[0] <= self.size[1]:
                self.size = (self.size[0] * 2, self.size[1])
            else:
                self.size = (self.size[0], self.size[1] * 2)
        elif method == MaxRects.EXPAND_LONG_SIDE:
            if self.size[0] >= self.size[1]:
                self.size = (self.size[0] * 2, self.size[1])
            else:
                self.size = (self.size[0], self.size[1] * 2)
        else:
            raise ValueError("Unexpected Method")

        for max_rect in self.max_rect_list:
            if max_rect.right == old_size[0]:
                max_rect.right = self.size[0]
            if max_rect.bottom == old_size[1]:
                max_rect.bottom = self.size[1]

        if old_size[0] != self.size[0]:
            new_rect = Rect(old_size[0], 0, self.size[0] - old_size[0], self.size[1])
            self.max_rect_list.append(new_rect)

        if old_size[1] != self.size[1]:
            new_rect = Rect(0, old_size[1], self.size[0], self.size[1] - old_size[1])
            self.max_rect_list.append(new_rect)

        self.max_rect_list = list(filter(self._max_rect_list_pruning, self.max_rect_list))

    def cut(self, main_rect, sub_rect, border=0):
        if not main_rect.is_overlaped(sub_rect):
            return [main_rect, ]

        result = []
        if main_rect.left < sub_rect.left:
            tmp = main_rect.clone()
            tmp.right = sub_rect.left - border
            result.append(tmp)
        if main_rect.top < sub_rect.top:
            tmp = main_rect.clone()
            tmp.bottom = sub_rect.top - border
            result.append(tmp)
        if main_rect.right > sub_rect.right:
            tmp = main_rect.clone()
            tmp.left = sub_rect.right + border
            result.append(tmp)
        if main_rect.bottom > sub_rect.bottom:
            tmp = main_rect.clone()
            tmp.top = sub_rect.bottom + border
            result.append(tmp)

        return result

    def rank(self, main_rect, sub_rect):
        """
        BSSF
        :param main_rect:
        :param sub_rect:
        :return:
        """
        tmp = min(main_rect.width - sub_rect.width, main_rect.height - sub_rect.height)
        assert tmp < MAX_RANK
        if tmp < 0:
            return MAX_RANK
        else:
            return tmp

    def find_best_rank(self, image_rect):
        best_rank = MAX_RANK
        best_index = -1
        for i, rect in enumerate(self.max_rect_list):
            rank = self.rank(rect, image_rect)
            if rank < best_rank:
                best_rank = rank
                best_index = i
        return best_index, best_rank

    def find_best_rank_with_rotate(self, image_rect):
        image_rect_r = image_rect.clone()
        image_rect_r.rotate()

        index, rank = self.find_best_rank(image_rect)
        index_r, rank_r = self.find_best_rank(image_rect_r)

        if rank < rank_r:
            return index, rank, False
        else:
            return index_r, rank, True

    def place_image_rect(self, rect_index, image_rect):
        rect = self.max_rect_list[rect_index]
        image_rect.x, image_rect.y = rect.x, rect.y

        _max_rect_list = []
        for i, rect in enumerate(self.max_rect_list):
            _max_rect_list.extend(self.cut(rect, image_rect))

        self.max_rect_list = _max_rect_list
        self.max_rect_list = list(filter(self._max_rect_list_pruning, _max_rect_list))
        self.image_rect_list.append(image_rect)

    def _max_rect_list_pruning(self, rect):
        for max_rect in self.max_rect_list:
            if rect != max_rect and rect in max_rect:
                return False

        return True

    def dump_plist(self):
        plist_data = {}

        frames = {}
        for image_rect in self.image_rect_list:
            path = image_rect.image_path
            frames[path] = dict(
                frame="{{%d,%d},{%d,%d}}" % (image_rect.x, image_rect.y, image_rect.width, image_rect.height),
                offset="{%d,%d}" % (0, 0),
                rotated=bool(image_rect.rotate),
                sourceColorRect="{{%d,%d},{%d,%d}}" % (0, 0, image_rect.width, image_rect.height),
                sourceSize="{%d,%d}" % (image_rect.width, image_rect.height),
            )

        plist_data["frames"] = frames
        plist_data["metadata"] = dict(
            format=int(2),
            textureFileName="",
            realTextureFileName="",
            size="{%d,%d}" % self.size,
        )

        return plist_data

    def dump_image(self, bg_color=0xffffffff):
        from PIL import Image
        packed_image = Image.new('RGBA', self.size, bg_color)

        for image_rect in self.image_rect_list:
            image = image_rect.image.crop()
            if image_rect.rotated:
                image = image.transpose(Image.ROTATE_90)
            packed_image.paste(image, (image_rect.left, image_rect.top, image_rect.right, image_rect.bottom))

        return packed_image