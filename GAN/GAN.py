import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.datasets as datasets
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
from torch.utils.tensorboard import SummaryWriter


# Things to try
# 1. What happens if you use larger networks?
# 2. Better normalization with BatchNorm
# 3. Different learning rate (is there a better one)?
# 4. Change architecture to a CNN

class Discriminator(nn.Module):
    def __init__(self, img_dim):  # mnist数据集 in_features为784
        super(Discriminator, self).__init__()
        self.disc = nn.Sequential(
            nn.Linear(img_dim, 128),
            nn.LeakyReLU(0.1),
            nn.Linear(128, 1),  # D最后映射到1维
            nn.Sigmoid(),  # 为了确保结果在0到1之间我们在D最后一层调用sigmoid()
        )

    def forward(self, x):
        return self.disc(x)


class Generator(nn.Module):
    def __init__(self, z_dim, img_dim):
        super(Generator, self).__init__()
        self.gen = nn.Sequential(
            nn.Linear(z_dim, 256),
            nn.LeakyReLU(0.1),
            nn.Linear(256, img_dim),
            nn.Tanh(),  # 为了确保输出的像素值在-1到1之间，在G的最后一层我们使用Tanh(因为我们要normalize
        )  # 使input处在-1到1之间，因此我们的输出要同理)

    def forward(self, x):
        return self.gen(x)


# Hyperparameters etc.
device = "cuda" if torch.cuda.is_available() else "cpu"
lr = 3e-4
z_dim = 64  # 128, 256
image_dim = 28 * 28 * 1  # 784
batch_size = 32
num_epochs = 50

disc = Discriminator(image_dim).to(device)
gen = Generator(z_dim, image_dim).to(device)
fixed_noise = torch.randn((batch_size, z_dim)).to(device)

transforms = transforms.Compose(
    [transforms.ToTensor(), transforms.Normalize((0.5,), (0.5,))]  # 传入两个只有一个元素的元组
)
dataset = datasets.MNIST(root="./dataset/", transform=transforms, download=True)
loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

opt_disc = optim.Adam(disc.parameters(), lr=lr)
opt_gen = optim.Adam(gen.parameters(), lr=lr)

criterion = nn.BCELoss()

writer_fake = SummaryWriter(f"./runs/GAN_MNIST/fake")
writer_real = SummaryWriter(f"./runs/GAN_MNIST/real")
step = 0

for epoch in range(num_epochs):
    for batch_idx, (real, _) in enumerate(loader):  # 不用labels因为GAN是无监督学习
        real = real.view(-1, 784).to(device)
        batch_size = real.shape[0]

        # Train Discriminator: max log(D(real)) + log(1 - D(G(z)))
        noise = torch.randn(batch_size, z_dim).to(device)
        fake = gen(noise)
        disc_real = disc(real).view(-1)  # 把列向量转换为行向量，其实没必要
        lossD_real = criterion(disc_real, torch.ones_like(disc_real))  # ones_like生成全为1的同形tensor，BCEloss前有负号，
        disc_fake = disc(fake.detach()).view(-1)  # 所以从最大化转换为最小化  因为要反复利用fake所以要detach
        lossD_fake = criterion(disc_fake, torch.zeros_like(disc_fake))
        lossD = (lossD_real + lossD_fake) / 2  # 其实不影响训练，也没有必要除????
        disc.zero_grad()
        lossD.backward()  # 上面不detach 这里retain_graph = True 也可
        opt_disc.step()

        # Train Generator min log(1-D(G(z))) <--> max log(D(G(z))) max G的loss
        output = disc(fake).view(-1)
        lossG = criterion(output, torch.ones_like(output))
        gen.zero_grad()
        lossG.backward()
        opt_gen.step()

        if batch_idx == 0:
            print(f"Epoch[{epoch+1}/{num_epochs}] Loss D: {lossD:.4f}, Loss G: {lossG:.4f}")

            with torch.no_grad():
                fake = gen(fixed_noise).reshape(-1, 1, 28, 28)
                data = real.reshape(-1, 1, 28, 28)
                img_grid_fake = torchvision.utils.make_grid(fake, normalize=True)
                img_grid_real = torchvision.utils.make_grid(data, normalize=True)

                writer_fake.add_image(
                    "Mnist Fake Images3", img_grid_fake, global_step=step
                )

                writer_real.add_image(
                    "Mnist real Images3", img_grid_real, global_step=step
                )

                step += 1
