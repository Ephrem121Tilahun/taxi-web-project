import mongoose from 'mongoose';

export const connectDB = async () => {
  try {
    await mongoose.connect('mongodb+srv://yeneanguach:Yeneanguach01@cluster0.lkvy3.mongodb.net/food-del');
    console.log('DB Connected');
  } catch (error) {
    console.error('DB Connection Error:', error);
  }
};
